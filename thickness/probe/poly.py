# poly.py -- convex polyhedra, every face removed in turn, each result against the
# volume booleans give (README.md sec 82). One shape a run: SHAPE, OUT, TS ("0.5 1").
#   Inward, either join: the polyhedron less what is left of it with every plane that
#     stays moved in by t.
#   Intersection outward: every plane that stays moved out by t, the removed face's as
#     it is, less the polyhedron.
#   Arc outward: the polyhedron grown by t (its faces pushed out, a cylinder round every
#     edge, a ball at every vertex), cut off at the removed face's plane, less the
#     polyhedron -- where no face beside the removed one stands at less than a right
#     angle to it: there the neighbour's offset is carried on to the removed face's
#     plane, more than the cylinder's sector, and the run is given no reference (NOREF).
import FreeCAD, Part, os, math

V = FreeCAD.Vector


def poly(pts, h):
    return Part.Face(Part.makePolygon([V(*p) for p in pts] + [V(*pts[0])])).extrude(V(0, 0, h))


def box_chamfer(d1, d2, which):
    b = Part.makeBox(30, 20, 10)
    top = [
        e for e in b.Edges if abs(e.BoundBox.ZMin - 10) < 1e-9 and abs(e.BoundBox.ZMax - 10) < 1e-9
    ]
    edges = {"top": top, "all": b.Edges, "one": top[:1], "two": top[:2]}[which]
    return b.makeChamfer(d1, d2, edges)


def frustum(bx, by, tx, ty, h, dx=0.0, dy=0.0):
    b = [V(-bx / 2, -by / 2, 0), V(bx / 2, -by / 2, 0), V(bx / 2, by / 2, 0), V(-bx / 2, by / 2, 0)]
    t = [
        V(dx - tx / 2, dy - ty / 2, h),
        V(dx + tx / 2, dy - ty / 2, h),
        V(dx + tx / 2, dy + ty / 2, h),
        V(dx - tx / 2, dy + ty / 2, h),
    ]
    faces = [Part.Face(Part.makePolygon(b + [b[0]])), Part.Face(Part.makePolygon(t + [t[0]]))]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(Part.Face(Part.makePolygon([b[i], b[j], t[j], t[i], b[i]])))
    s = Part.Solid(Part.Shell(faces))
    if s.Volume < 0:
        s.reverse()
    return s


def corner_cut():
    b = Part.makeBox(30, 20, 10)
    t = Part.Solid(
        Part.Shell(
            [
                Part.Face(Part.makePolygon(p + [p[0]]))
                for p in (
                    [V(30, 20, 10), V(22, 20, 10), V(30, 14, 10)],
                    [V(30, 20, 10), V(30, 14, 10), V(30, 20, 5)],
                    [V(30, 20, 10), V(30, 20, 5), V(22, 20, 10)],
                    [V(22, 20, 10), V(30, 20, 5), V(30, 14, 10)],
                )
            ]
        )
    )
    if t.Volume < 0:
        t.reverse()
    return b.cut(t).removeSplitter()


SHAPES = {
    "box": lambda: Part.makeBox(30, 20, 10),
    "chamfer_top_2x2": lambda: box_chamfer(2, 2, "top"),
    "chamfer_top_2x1": lambda: box_chamfer(2, 1, "top"),
    "chamfer_top_1x3": lambda: box_chamfer(1, 3, "top"),
    "chamfer_all_2x2": lambda: box_chamfer(2, 2, "all"),
    "chamfer_one": lambda: box_chamfer(2, 2, "one"),
    "chamfer_two": lambda: box_chamfer(2, 3, "two"),
    "frustum_10": lambda: frustum(30, 20, 26, 16, 10),
    "frustum_skew": lambda: frustum(30, 20, 20, 12, 10, 3, 2),
    "wedge": lambda: poly([(0, 0, 0), (30, 0, 0), (30, 5, 0), (0, 15, 0)], 12),
    "hex": lambda: poly(
        [
            (10 * math.cos(math.radians(60 * i)), 10 * math.sin(math.radians(60 * i)), 0)
            for i in range(6)
        ],
        8,
    ),
    "pent": lambda: poly(
        [
            (10 * math.cos(math.radians(72 * i)), 10 * math.sin(math.radians(72 * i)), 0)
            for i in range(5)
        ],
        8,
    ),
    "tri": lambda: poly([(0, 0, 0), (20, 0, 0), (6, 14, 0)], 10),
    "corner_cut": corner_cut,
    "hex_chamfer": lambda: (
        lambda s: s.makeChamfer(
            1.5,
            [
                e
                for e in s.Edges
                if abs(e.BoundBox.ZMin - 8) < 1e-9 and abs(e.BoundBox.ZMax - 8) < 1e-9
            ],
        )
    )(
        poly(
            [
                (10 * math.cos(math.radians(60 * i)), 10 * math.sin(math.radians(60 * i)), 0)
                for i in range(6)
            ],
            8,
        )
    ),
}


def half(shape, f, shift):
    n = f.normalAt(0, 0)
    p = f.CenterOfMass + n * shift
    m = shape.BoundBox.DiagonalLength
    u = n.cross(V(1, 0, 0))
    if u.Length < 1e-6:
        u = n.cross(V(0, 1, 0))
    u.normalize()
    w = n.cross(u)
    c = [
        p + u * (4 * m) + w * (4 * m),
        p - u * (4 * m) + w * (4 * m),
        p - u * (4 * m) - w * (4 * m),
        p + u * (4 * m) - w * (4 * m),
    ]
    return Part.Face(Part.makePolygon(c + [c[0]])).extrude(n * (-8 * m))


def planes(shape, fi, t):
    b = shape.BoundBox
    m = b.DiagonalLength
    rest = Part.makeBox(
        b.XLength + 2 * m,
        b.YLength + 2 * m,
        b.ZLength + 2 * m,
        V(b.XMin - m, b.YMin - m, b.ZMin - m),
    )
    for i, f in enumerate(shape.Faces):
        rest = rest.common(half(shape, f, 0.0 if i == fi else t))
    return rest.Volume


def want(shape, fi, t, join):
    if t < 0:
        return shape.Volume - planes(shape, fi, t)
    if join == 2:
        return planes(shape, fi, t) - shape.Volume
    cap = shape.Faces[fi]
    for g in shape.Faces:
        if any(e.isSame(x) for e in cap.Edges for x in g.Edges) and not g.isSame(cap):
            if cap.normalAt(0, 0).dot(g.normalAt(0, 0)) < -1e-9:
                return None
    parts = [f.extrude(f.normalAt(0, 0) * t) for f in shape.Faces]
    for e in shape.Edges:
        a, b = e.Vertexes[0].Point, e.Vertexes[1].Point
        parts.append(Part.makeCylinder(t, (b - a).Length, a, b - a))
    parts += [Part.makeSphere(t, v.Point) for v in shape.Vertexes]
    return shape.fuse(parts).common(half(shape, shape.Faces[fi], 0.0)).Volume - shape.Volume


name = os.environ["SHAPE"]
out = open(os.environ["OUT"], "w")
s0 = SHAPES[name]()
out.write("# %s faces %d valid %s vol %.4f\n" % (name, len(s0.Faces), s0.isValid(), s0.Volume))
for fi in range(len(s0.Faces)):
    for t in [float(x) for x in os.environ.get("TS", "0.5 1").split()]:
        for sign in (1, -1):
            ref = {}
            for join in (0, 2):
                s = SHAPES[name]()
                tag = "%s f%d %+g j%d" % (name, fi + 1, sign * t, join)
                key = (sign, join if sign > 0 else 0)
                if key not in ref:
                    try:
                        ref[key] = want(s, fi, sign * t, join)
                    except Exception as e:
                        ref[key] = None
                w = ref[key]
                try:
                    r = s.makeThickness([s.Faces[fi]], sign * t, 1e-7, False, False, 0, join)
                    if not r.isValid():
                        res = "INVALID vol %.4f" % r.Volume
                    elif w is None:
                        res = "valid vol %.4f NOREF" % r.Volume
                    elif abs(r.Volume - w) <= 1e-4 * max(1.0, abs(w)):
                        res = "RIGHT vol %.4f" % r.Volume
                    else:
                        res = "WRONG vol %.4f want %.4f" % (r.Volume, w)
                except Exception:
                    res = "REFUSED" + ("" if w is None else " want %.4f" % w)
                out.write("%s | %s\n" % (tag, res))
                out.flush()
out.write("# done\n")
