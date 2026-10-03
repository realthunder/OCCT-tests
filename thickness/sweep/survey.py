# survey.py -- two things that must not change a thickness (models/Thickness.md,
# sec 22, 24 and 26):
#
#   SURVEY=split  a vertex at the middle of an edge; every edge in turn
#   SURVEY=order  the solid's faces in another order; every rotation of the
#                 face list and its reverse (PERM=1: every permutation, for a
#                 solid of five faces at the most)
#
# Each face removed, +-0.5, the Arc and the Intersection join, compared with
# the shape as made; a run the shape as made gets no valid answer for is not
# counted. Run with FreeCADCmd:
#
#   SHAPE=<key> SURVEY=split|order [PLACE=placed|turned] [THICK_FREEZE=1] \
#       FreeCADCmd survey.py
#
# prints a line for each run that differs and "SUMMARY <key> good=N bad=M".
# SHAPE=list prints the keys.
import itertools
import math
import os

import FreeCAD
import Part

V = FreeCAD.Vector


def out(s):
    os.write(1, (s + "\n").encode())


def _ball(a1, a2, a3):
    return Part.makeSphere(5, V(), V(0, 0, 1), a1, a2, a3)


SHAPES = {
    "ball270": lambda: _ball(-90, 90, 270),
    "ball240": lambda: _ball(-90, 90, 240),
    "ball150": lambda: _ball(-90, 90, 150),
    "lune90": lambda: _ball(-90, 90, 90),
    "halfball": lambda: _ball(-90, 90, 180),
    "halfdome": lambda: _ball(0, 90, 180),
    "quartdome": lambda: _ball(0, 90, 90),
    "dome270": lambda: _ball(0, 90, 270),
    "dome": lambda: _ball(0, 90, 360),
    "box": lambda: Part.makeBox(10, 8, 6),
    "cyl": lambda: Part.makeCylinder(4, 6),
    "cone": lambda: Part.makeCone(0, 4, 6),
    "eqball": lambda: _ball(-90, 90, 180).generalFuse(
        [Part.ArcOfCircle(Part.Circle(V(), V(0, 0, 1), 5), 0, math.pi).toShape()])[0].Solids[0],
    "luneball": lambda: _ball(-90, 90, 180).generalFuse(
        [Part.Arc(V(0, 0, -5), V(0, 5, 0), V(0, 0, 5)).toShape()])[0].Solids[0],
    "filletbox": lambda: (lambda b: b.makeFillet(2, [b.Edges[i] for i in (0, 2, 4, 6)]))(
        Part.makeBox(10, 8, 6)),
    "splitbox": lambda: Part.makeBox(4, 8, 6).fuse(Part.makeBox(6, 8, 6, V(4, 0, 0))),
    "bullet": lambda: Part.makeCylinder(5, 4, V(0, 0, -4)).fuse(_ball(0, 90, 360)).removeSplitter(),
    "cap": lambda: _ball(30, 90, 360),
    "halfcap": lambda: _ball(30, 90, 180),
    "conehole": lambda: Part.makeCone(6, 3, 8).cut(Part.makeCylinder(1.5, 8)),
    "ann": lambda: Part.makeCylinder(5, 6).cut(Part.makeCylinder(2, 6)),
    "lbox": lambda: Part.makeBox(10, 4, 6).fuse(Part.makeBox(4, 10, 6)).removeSplitter(),
    "halfball1": lambda: _ball(-90, 90, 180).removeSplitter(),
    "cutball": lambda: Part.makeSphere(5).cut(Part.makeBox(20, 20, 20, V(-10, -20, -10))),
    "torus": lambda: Part.makeTorus(6, 2),
}


def place(base, how):
    p = FreeCAD.Placement(V(3, 4, 5), FreeCAD.Rotation(V(1, 2, 3), 40))
    if how == "placed":
        base = base.copy()
        base.Placement = p
    elif how == "turned":
        base = base.copy()
        base.transformShape(p.Matrix, True)
    return base


def run(s, fi, off, j):
    try:
        r = s.makeThickness([s.Faces[fi]], off, 1e-3, False, False, 0, j)
        return (r.isValid(), round(r.Volume, 4))
    except Exception as e:
        return ("EXC", str(e).strip().splitlines()[-1][:30])


def variants_split(base):
    """(label, shape, index in shape.Faces of each face of base or None)"""
    for ei, e in enumerate(base.Edges):
        if e.Degenerated:
            continue
        p = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
        s = base.generalFuse([Part.Vertex(p)])[0].Solids[0]
        order = []
        for f in base.Faces:
            m = [i for i, g in enumerate(s.Faces)
                 if abs(g.Area - f.Area) < 1e-6 and (g.CenterOfMass - f.CenterOfMass).Length < 1e-6]
            order.append(m[0] if m else None)
        yield "E%d" % (ei + 1), s, order


key = ""


def variants_order(base):
    n = len(base.Faces)
    if os.environ.get("PERM") == "1" and n <= 5:
        orders = list(itertools.permutations(range(n)))[1:]
    else:
        orders = [tuple((i + k) % n for i in range(n)) for k in range(1, n)]
        orders.append(tuple(reversed(range(n))))
    for o in orders:
        s = Part.Solid(Part.Shell([base.Faces[i] for i in o]))
        label = "order " + ",".join(str(i + 1) for i in o)
        if not s.isValid() or abs(s.Volume - base.Volume) > 1e-6:
            out("%s %s: not the solid" % (key, label))
            continue
        yield label, s, [o.index(i) for i in range(n)]


def main():
    global key
    key = os.environ.get("SHAPE", "list")
    if key == "list":
        out(" ".join(SHAPES))
        os._exit(0)
    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Part").SetBool(
        "ImmutableShapeValues", os.environ.get("THICK_FREEZE", "0") != "0")
    base = place(SHAPES[key](), os.environ.get("PLACE"))
    RUNS = [(fi, off, j) for fi in range(len(base.Faces)) for off in (0.5, -0.5) for j in (0, 2)]
    ref = {r: run(base, *r) for r in RUNS}
    variants = variants_order if os.environ.get("SURVEY", "split") == "order" else variants_split
    good = bad = 0
    for label, s, order in variants(base):
        for fi, off, j in RUNS:
            r0 = ref[fi, off, j]
            if r0[0] is not True:
                continue
            if order[fi] is None:
                out("%s %s F%d: face not found" % (key, label, fi + 1))
                continue
            r = run(s, order[fi], off, j)
            if r[0] is True and abs(r[1] - r0[1]) < 2e-3 * max(1, abs(r0[1])):
                good += 1
            else:
                bad += 1
                out("BAD %s %s F%d %+.1f j%d: %s for %s" % (key, label, fi + 1, off, j, r, r0[1]))
    out("SUMMARY %s good=%d bad=%d" % (key, good, bad))
    os._exit(0)


# probe.py takes the shapes and the variants from here.
if not os.environ.get("SURVEY_AS_MODULE"):
    main()
