# FreeCADCmd patterns.py -- reads a model's PartDesign patterns by points
# taken at random (../README.md, "Where the models stand").
#
# Every object is made again; then, for each pattern (Mirrored,
# LinearPattern, PolarPattern, MultiTransform of those), NPTS points (1500)
# in the box of its support and its result are asked whether they are inside
# the result where they should be: inside the support with every copy of
# each original's add shapes fused in and of its sub shapes cut out, the
# originals in the order they have in the body. The transformations are
# worked out here from the pattern's properties, not asked of it. Whether
# the first copy -- the original itself -- is made again depends on the
# pattern's version, and the sense of a direction on its reference: both
# ways are tried and the better taken. A pattern or a dress-up among the
# originals brings both kinds of shape, packed in its AddSubShape as
# Transformed::getAddSubShape() and DressUp::getAddSubShape() unpack it.
# Not read: a TransformOffset, spacing lists, suppressed copies, a second
# direction, an intersecting shape, a pattern not made again.
#
# env: MODEL   the .FCStd
#      NPTS    points per pattern (default 1500)
#      DETAIL  a pattern's name: its shapes, and for the first twelve points
#              that differ which copies of which original hold them
# Prints one line a pattern, "ok", "BAD" or "skip", and "DONE". Run it under
# a pty with its own FREECAD_USER_HOME, a memory cap and a timeout.
import traceback, os, random, math, itertools


def emit(s):
    os.write(1, ("@@ " + str(s).replace("\n", " | ") + "\n").encode())


try:
    import FreeCAD as App, Part

    V = App.Vector
    M = os.environ["MODEL"]
    N = int(os.environ.get("NPTS", "1500"))
    tag = os.path.basename(M)[:8]
    d = App.openDocument(M)
    for o in d.Objects:
        o.touch()
    d.recompute()

    def inside(s, p):
        return s.isInside(p, 1e-7, True)

    def role(o):
        r = getattr(o, "Role", "") or o.Name
        return r.rstrip("0123456789")

    def sketch_axes(sk):
        R = sk.Placement.Rotation
        B = sk.Placement.Base
        return B, R.multVec(V(1, 0, 0)), R.multVec(V(0, 1, 0)), R.multVec(V(0, 0, 1))

    def plane_of(ref):
        obj, subs = ref
        sub = subs[0] if subs else ""
        if obj.isDerivedFrom("Part::Part2DObject"):
            B, H, Vd, Nn = sketch_axes(obj)
            return {"H_Axis": (B, Vd), "V_Axis": (B, H), "": (B, Nn)}.get(sub)
        if obj.isDerivedFrom("PartDesign::Plane"):
            return obj.Placement.Base, obj.Placement.Rotation.multVec(V(0, 0, 1))
        if obj.isDerivedFrom("App::Plane"):
            n = {"XY_Plane": V(0, 0, 1), "XZ_Plane": V(0, 1, 0), "YZ_Plane": V(1, 0, 0)}.get(
                role(obj)
            )
            return (V(0, 0, 0), n) if n else None
        if obj.isDerivedFrom("Part::Feature") and sub.startswith("Face"):
            s = obj.getSubObject(sub).Surface
            if isinstance(s, Part.Plane):
                return s.Position, s.Axis
        return None

    def line_of(ref):
        obj, subs = ref
        sub = subs[0] if subs else ""
        if obj.isDerivedFrom("Part::Part2DObject"):
            B, H, Vd, Nn = sketch_axes(obj)
            return {"H_Axis": (B, H), "V_Axis": (B, Vd), "N_Axis": (B, Nn)}.get(sub)
        if obj.isDerivedFrom("PartDesign::Line"):
            return obj.Placement.Base, obj.Placement.Rotation.multVec(V(0, 0, 1))
        if obj.isDerivedFrom("App::Line"):
            a = {"X_Axis": V(1, 0, 0), "Y_Axis": V(0, 1, 0), "Z_Axis": V(0, 0, 1)}.get(role(obj))
            return (V(0, 0, 0), a) if a else None
        if obj.isDerivedFrom("Part::Feature") and sub.startswith("Edge"):
            c = obj.getSubObject(sub).Curve
            if isinstance(c, Part.Line):
                return c.Location, c.Direction
            if isinstance(c, Part.Circle):
                return c.Center, c.Axis
        return None

    def kids(s):
        return list(s.SubShapes)

    def empty(s):
        return s.isNull() or (s.ShapeType == "Compound" and not kids(s))

    # the add/sub shapes of a feature as a pattern takes them: [(shape, "+" or "-")], or None
    def addsub_parts(g):
        a = getattr(g, "AddSubShape", None)
        if a is None or a.isNull():
            return None
        if g.isDerivedFrom("PartDesign::Transformed"):
            if a.ShapeType != "Compound":
                return [(a, "+")]
            subs = kids(a)
            out = []
            if 0 < len(subs) <= 3:
                s0 = subs[0]
                proceed = False
                if s0.ShapeType != "Compound":
                    out.append((s0, "+"))
                    proceed = True
                elif not kids(s0):
                    proceed = True
                if proceed and len(subs) > 1:
                    s1 = subs[1]
                    if not empty(s1):
                        out.append((s1, "-"))
                    elif len(subs) > 2:
                        return None  # intersecting
            if not out:
                for sub in subs:
                    if sub.ShapeType != "Compound":
                        out.append((sub, "+"))
                        continue
                    k = kids(sub)
                    if len(k) > 0 and not empty(k[0]):
                        out.append((k[0], "+"))
                        continue
                    if len(k) > 1 and not empty(k[1]):
                        out.append((k[1], "-"))
                        continue
                    if len(k) > 2:
                        return None  # intersecting
            return out or None
        if g.isDerivedFrom("PartDesign::DressUp"):
            if a.ShapeType != "Compound":
                return [(a, "+")]
            k = kids(a)
            out = []
            if len(k) > 0 and k[0].Solids:
                out.append((k[0], "+"))
            if len(k) > 1 and k[1].Solids:
                out.append((k[1], "-"))
            return out or None
        if not hasattr(g, "AddSubType"):
            return None
        return [(a, "-" if g.AddSubType == "Subtractive" else "+")]

    # the inverse maps of a feature's transformations, identity first; None if not understood
    def inverses(o, sign):
        t = o.TypeId
        if not o.TransformOffset.isIdentity():
            return None
        if getattr(o, "SuppressedIndices", []):
            return None
        if t == "PartDesign::Mirrored":
            pl = plane_of(o.MirrorPlane)
            if not pl:
                return None
            c, n = pl
            n = V(n)
            n.normalize()
            return [lambda p: p, lambda p, c=c, n=n: p - n * (2 * (p - c).dot(n))]
        if t in ("PartDesign::LinearPattern", "PartDesign::PolarPattern"):
            if list(o.Spacings) not in ([], [-1.0, -1.0]) or list(o.SpacingPattern):
                return None
            n = o.Occurrences
            if t.endswith("LinearPattern"):
                if o.Occurrences2 != 1:
                    return None
                ln = line_of(o.Direction)
                if not ln:
                    return None
                a = V(ln[1])
                a.normalize()
                step = (
                    (o.Length.Value / (n - 1) if n > 1 else 0.0)
                    if o.Mode == "Extent"
                    else o.Offset.Value
                )
                if o.Reversed:
                    step = -step
                return [lambda p, i=i: p - a * (sign * step * i) for i in range(n)]
            ln = line_of(o.Axis)
            if not ln:
                return None
            c, a = ln
            a = V(a)
            a.normalize()
            ang = o.Angle.Value
            step = (
                (360.0 / n if abs(abs(ang) - 360.0) < 1e-7 else (ang / (n - 1) if n > 1 else 0.0))
                if o.Mode == "Extent"
                else o.Offset.Value
            )
            if o.Reversed:
                step = -step

            def rot(p, i):
                r = App.Rotation(a, -sign * step * i)
                return c + r.multVec(p - c)

            return [lambda p, i=i: rot(p, i) for i in range(n)]
        if t == "PartDesign::MultiTransform":
            sets = [inverses(x, sign) for x in o.Transformations]
            if any(s is None for s in sets):
                return None
            out = []
            for combo in itertools.product(*sets):

                def f(p, combo=combo):
                    for g in combo:
                        p = g(p)  # the inverse of the last applied first
                    return p

                out.append(f)
            return out
        return None

    n = 0
    for o in d.Objects:
        if not o.isDerivedFrom("PartDesign::Transformed"):
            continue
        if not hasattr(o, "Shape") or o.Shape.isNull():
            continue
        kind = o.TypeId.split("::")[-1]
        if "Invalid" in o.State or not o.isValid():
            emit("skip %s %s [%s]: in error" % (tag, o.Name, kind))
            continue
        if "Touched" in o.State:
            emit("skip %s %s [%s]: not made again (%s)" % (tag, o.Name, kind, o.State))
            continue
        b = getattr(o, "BaseFeature", None)
        if b is None or b.Shape.isNull():
            emit("skip %s %s [%s]: no base" % (tag, o.Name, kind))
            continue
        tools = []
        body = o.getParentGeoFeatureGroup()
        order = {x.Name: i for i, x in enumerate(body.Group)} if body else {}
        for g in sorted(o.Originals, key=lambda x: order.get(x.Name, 10**6)):
            if not g.isDerivedFrom("Part::Feature"):
                continue
            parts = addsub_parts(g)
            if not parts:
                a = getattr(g, "AddSubShape", None)
                if a is not None and not a.isNull():
                    emit(
                        "   %s AddSubShape %s: %s"
                        % (
                            g.Name,
                            a.ShapeType,
                            [
                                (
                                    k.ShapeType,
                                    len(k.Solids),
                                    len(k.Faces),
                                    (
                                        [(q.ShapeType, len(q.Solids)) for q in kids(k)]
                                        if k.ShapeType == "Compound"
                                        else ""
                                    ),
                                )
                                for k in kids(a)
                            ],
                        )
                    )
                tools = None
                emit(
                    "skip %s %s [%s]: original %s (%s): add/sub shape not understood"
                    % (tag, o.Name, kind, g.Name, g.TypeId)
                )
                break
            for a, k in parts:
                aw = a.copy()
                aw.Placement = g.Placement.multiply(a.Placement)
                tools.append((aw, k == "-", g.Name))
        if not tools:
            if tools is not None:
                emit("skip %s %s [%s]: no originals" % (tag, o.Name, kind))
            continue
        res = o.Shape
        sup = b.Shape
        bb = App.BoundBox()
        bb.add(res.BoundBox)
        bb.add(sup.BoundBox)
        bb.enlarge(0.01 * max(bb.DiagonalLength, 1e-3))
        rnd = random.Random(12345)
        pts = [
            V(
                rnd.uniform(bb.XMin, bb.XMax),
                rnd.uniform(bb.YMin, bb.YMax),
                rnd.uniform(bb.ZMin, bb.ZMax),
            )
            for i in range(N)
        ]
        rin = [inside(res, p) for p in pts]
        sin_ = [inside(sup, p) for p in pts]
        best = None
        for sign in (1, -1):
            inv = inverses(o, sign)
            if inv is None:
                break
            hit = []  # per tool, per point: in any copy but the first / in the first
            for aw, sub, name in tools:
                rest = [any(inside(aw, f(p)) for f in inv[1:]) for p in pts]
                first = [inside(aw, p) for p in pts]
                hit.append((rest, first, sub))
            for with_first in (False, True):
                bad = 0
                firstbad = None
                for i, p in enumerate(pts):
                    v = sin_[i]
                    for rest, first, sub in hit:
                        h = rest[i] or (with_first and first[i])
                        v = (v and not h) if sub else (v or h)
                    if v != rin[i]:
                        bad += 1
                        if firstbad is None:
                            firstbad = (tuple(round(x, 3) for x in p), v, rin[i])
                if best is None or bad < best[0]:
                    best = (bad, sign, with_first, firstbad, len(inv))
        if best is None:
            emit("skip %s %s [%s]: transformation not understood" % (tag, o.Name, kind))
            continue
        if os.environ.get("DETAIL") == o.Name:
            inv = inverses(o, best[1])
            emit(
                "   base %s %s vol %.4f ; result vol %.4f ; state %s"
                % (b.Name, b.TypeId, sup.Volume, res.Volume, o.State)
            )
            for aw, sub, name in tools:
                emit(
                    "   tool %s%s vol %.4f solids %d valid %s box %s"
                    % (
                        "-" if sub else "+",
                        name,
                        aw.Volume,
                        len(aw.Solids),
                        aw.isValid(),
                        aw.BoundBox,
                    )
                )
            shown = 0
            for i, p in enumerate(pts):
                v = sin_[i]
                trace = ["sup %d" % v]
                for aw, sub, name in tools:
                    cop = [k for k, f in enumerate(inv) if inside(aw, f(p))]
                    h = any(k > 0 for k in cop) or (best[2] and 0 in cop)
                    v = (v and not h) if sub else (v or h)
                    if cop:
                        trace.append("%s%s copies %s -> %d" % ("-" if sub else "+", name, cop, v))
                if v != rin[i] and shown < 12:
                    shown += 1
                    emit(
                        "   point (%.3f %.3f %.3f): want %d got %d ; %s"
                        % (p.x, p.y, p.z, v, rin[i], " ; ".join(trace))
                    )
        vol = bb.XLength * bb.YLength * bb.ZLength
        emit(
            "%s %s %s [%s, version %s, %d originals %s, %d copies]: vol %.4f, mismatches %d of %d (about %.2f mm3), sign %+d, first copy %s%s"
            % (
                "BAD" if best[0] else "ok ",
                tag,
                o.Name,
                kind,
                getattr(o, "_Version", "?"),
                len(o.Originals),
                [("-" if s else "+") + nm for a, s, nm in tools],
                best[4],
                res.Volume,
                best[0],
                N,
                vol * best[0] / N,
                best[1],
                "in" if best[2] else "out",
                " first %s" % (best[3],) if best[3] else "",
            )
        )
        n += 1
    emit("DONE %s: %d checked" % (tag, n))
except Exception:
    emit(traceback.format_exc())
