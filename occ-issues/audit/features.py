# FreeCADCmd features.py -- reads a model's adding and removing features by
# points taken at random (../README.md, "Where the models stand").
#
# Every object is made again; then, for each PartDesign add/sub feature and
# each Part boolean, NPTS points (1500) in the box of its inputs and its
# result are asked whether they are inside the result where the inputs say
# they should be: inside the base or the feature's own solid for an additive
# feature, inside the base and not the solid for a subtractive one. A
# feature that comes out with no error and a valid shape and is wrong --
# nothing added, nothing removed -- shows here and nowhere else. Patterns
# are patterns.py's; dress-ups (fillet, chamfer, draft, thickness) are not
# read.
#
# env: MODEL  the .FCStd
#      NPTS   points per feature (default 1500)
# Prints one line a feature, "ok" or "BAD", and "DONE". Run it under a pty
# with its own FREECAD_USER_HOME, a memory cap and a timeout.
import traceback, os, random


def emit(s):
    os.write(1, ("@@ " + str(s) + "\n").encode())


try:
    import FreeCAD as App, Part

    M = os.environ["MODEL"]
    N = int(os.environ.get("NPTS", "1500"))
    tag = os.path.basename(M)[:8]
    d = App.openDocument(M)
    for o in d.Objects:
        o.touch()
    d.recompute()

    def inside(s, p):
        return s.isInside(p, 1e-7, True)

    def check(name, kind, parts, res, want):
        # parts: list of shapes; want: function of list of bools
        try:
            bb = App.BoundBox()
            for s in parts + [res]:
                if not s.isNull():
                    bb.add(s.BoundBox)
            bb.enlarge(0.01 * max(bb.DiagonalLength, 1e-3))
            rnd = random.Random(12345)
            bad = 0
            nin = 0
            first = None
            for i in range(N):
                p = App.Vector(
                    rnd.uniform(bb.XMin, bb.XMax),
                    rnd.uniform(bb.YMin, bb.YMax),
                    rnd.uniform(bb.ZMin, bb.ZMax),
                )
                w = want([inside(s, p) for s in parts])
                r = inside(res, p)
                nin += 1 if w else 0
                if w != r:
                    bad += 1
                    if first is None:
                        first = (tuple(round(x, 3) for x in p), w, r)
            vol = bb.XLength * bb.YLength * bb.ZLength
            emit(
                "%s %s %s [%s]: vol %.4f, sampled wanted %.1f, mismatches %d of %d (about %.2f mm3)%s"
                % (
                    "BAD" if bad else "ok ",
                    tag,
                    name,
                    kind,
                    res.Volume,
                    vol * nin / N,
                    bad,
                    N,
                    vol * bad / N,
                    " first %s" % (first,) if first else "",
                )
            )
        except Exception as e:
            emit("ERR %s %s [%s]: %s" % (tag, name, kind, e))

    n = 0
    for o in d.Objects:
        if not hasattr(o, "Shape") or o.Shape.isNull():
            continue
        if "Invalid" in o.State or not o.isValid():
            continue
        if "Touched" in o.State:
            continue  # not made again: something under it is in error
        t = o.TypeId
        if o.isDerivedFrom("PartDesign::Transformed") or o.isDerivedFrom("PartDesign::DressUp"):
            continue
        if o.isDerivedFrom("PartDesign::FeatureAddSub"):
            b = getattr(o, "BaseFeature", None)
            a = o.AddSubShape
            if a.isNull():
                continue
            aw = a.copy()
            aw.Placement = o.Placement.multiply(a.Placement)
            sub = o.AddSubType == "Subtractive"
            if b is None or b.Shape.isNull():
                if sub:
                    continue
                check(o.Name, t.split("::")[-1] + " alone", [aw], o.Shape, lambda v: v[0])
            elif sub:
                check(
                    o.Name,
                    t.split("::")[-1] + " sub",
                    [b.Shape, aw],
                    o.Shape,
                    lambda v: v[0] and not v[1],
                )
            else:
                check(
                    o.Name,
                    t.split("::")[-1] + " add",
                    [b.Shape, aw],
                    o.Shape,
                    lambda v: v[0] or v[1],
                )
            n += 1
        elif t == "Part::Cut":
            check(o.Name, "Cut", [o.Base.Shape, o.Tool.Shape], o.Shape, lambda v: v[0] and not v[1])
            n += 1
        elif t in ("Part::Fuse", "Part::Common"):
            f = (lambda v: v[0] or v[1]) if t.endswith("Fuse") else (lambda v: v[0] and v[1])
            check(o.Name, t[6:], [o.Base.Shape, o.Tool.Shape], o.Shape, f)
            n += 1
        elif t in ("Part::MultiFuse", "Part::MultiCommon"):
            f = any if t.endswith("Fuse") else all
            check(o.Name, t[6:], [x.Shape for x in o.Shapes], o.Shape, f)
            n += 1
    emit("DONE %s: %d checked" % (tag, n))
except Exception:
    emit(traceback.format_exc())
