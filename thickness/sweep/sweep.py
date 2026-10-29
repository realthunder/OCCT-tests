# The thickness sweep: 24 solids, every face removed in turn, +1 and -1,
# intersection off and on, the Arc and the Intersection join -- 928 runs.
# Run under FreeCADCmd (sweep.sh restarts it after a crash). One line a run:
#   R <k> <tag> OK|LOOSE:<gap>|BAD:<why>|EXC <what> [vol=.. solids=.. shells=..] [INPUT-CHANGED]
# LOOSE is a valid result with an edge whose curve ends short of its vertex
# (loose_ends.py): check.py counts it wrong, as it does BAD.
# env: MODES="nj0 Ij2 ..." to restrict, START=<k>, THICK_FREEZE=1 to freeze
# shape values (unfrozen by default, as run_tests.py), SWEEP_PLACE=placed to
# give every solid a location (an object's placement) or =baked to turn and
# move its geometry instead: the volumes are the same wherever a solid lies.
# SWEEP_PLACEMENT="x y z ax ay az degrees" is where, (3 4 5) and 40 degrees
# about (1 2 3) when not given. THICK_FIX_LEVEL=<n> runs at the fork's offset
# fix level n (../../fix_level.py).
import os
import sys
import FreeCAD
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from loose_ends import loose, widest  # noqa: E402

V = FreeCAD.Vector
from freeze import set_for_run  # noqa: E402
set_for_run(os.environ.get("THICK_FREEZE", "0") != "0")
# THICK_FIX_LEVEL=<n>: the fork's offset fix level (fix_level.py)
from fix_level import from_env as _fix_level_from_env  # noqa: E402

_fix_level_from_env()


def out(s):
    os.write(1, (s + "\n").encode())


def ellipsepad():
    e = Part.Ellipse(V(0, 0, 0), 10, 5).toShape()
    return Part.Face(Part.Wire(e)).extrude(V(0, 0, 8))


def filletbox():
    b = Part.makeBox(10, 8, 6)
    return b.makeFillet(2, [b.Edges[i] for i in (0, 2, 4, 6)])


SHAPES = {
    "box": lambda: Part.makeBox(10, 8, 6),
    "cyl": lambda: Part.makeCylinder(4, 20),
    "hole": lambda: Part.makeCylinder(5, 10).cut(Part.makeCylinder(2, 10)),
    "lbox": lambda: Part.makeBox(10, 10, 5).cut(Part.makeBox(5, 5, 5, V(5, 5, 0))),
    "boxhole": lambda: Part.makeBox(10, 10, 5).cut(Part.makeCylinder(2, 5, V(5, 5, 0))),
    "boxhole2": lambda: Part.makeBox(10, 10, 5).cut(Part.makeCylinder(2, 3, V(5, 5, 2))),
    "pocket": lambda: Part.makeBox(10, 10, 6).cut(Part.makeBox(5, 5, 3, V(2.5, 2.5, 3))),
    "cone": lambda: Part.makeCone(5, 2, 8),
    "conehole": lambda: Part.makeCone(6, 3, 8).cut(Part.makeCylinder(1.5, 8)),
    "sphere": lambda: Part.makeSphere(5),
    "torus": lambda: Part.makeTorus(8, 2),
    "cylboss": lambda: Part.makeCylinder(6, 4).fuse(Part.makeCylinder(3, 4, V(0, 0, 4))),
    "cylpocket": lambda: Part.makeCylinder(6, 6).cut(Part.makeCylinder(3, 3, V(0, 0, 3))),
    "ellipse": ellipsepad,
    "fillet": filletbox,
    "tshape": lambda: Part.makeBox(12, 4, 4).fuse(
        Part.makeBox(4, 4, 10, V(4, 0, 0))).removeSplitter(),
    # A ball of 5 cut by planes through its axis and by its equator: a face
    # of a sphere that reaches a pole, with flat neighbours.
    "dome": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 360),
    "halfdome": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 180),
    "quartdome": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 90),
    "dome120": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 120),
    "dome270": lambda: Part.makeSphere(5, V(), V(0, 0, 1), 0, 90, 270),
    "lune90": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 90),
    # From pole to pole on a third and on half a turn: the half ball's sphere
    # has a whole great circle for its outline (MakeThickSolidOfSplit).
    "ball120": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 120),
    "halfball": lambda: Part.makeSphere(5, V(), V(0, 0, 1), -90, 90, 180),
}
MODES = os.environ.get("MODES", "").split()
PLACE = os.environ.get("SWEEP_PLACE", "")
PLACEMENT = FreeCAD.Placement(V(3, 4, 5), FreeCAD.Rotation(V(1, 2, 3), 40))
if os.environ.get("SWEEP_PLACEMENT"):  # "x y z ax ay az degrees"
    _p = [float(x) for x in os.environ["SWEEP_PLACEMENT"].split()]
    PLACEMENT = FreeCAD.Placement(V(*_p[:3]), FreeCAD.Rotation(V(*_p[3:6]), _p[6]))


def make(mk):
    s = mk()
    if PLACE == "placed":
        s.Placement = PLACEMENT
    elif PLACE == "baked":
        s.transformShape(PLACEMENT.Matrix, True)
    return s


def signature(s):
    tol = max([0.0] + [x.Tolerance for x in s.Vertexes + s.Edges + s.Faces])
    return (s.isValid(), round(s.Volume, 6), round(tol, 9))


start = int(os.environ.get("START", "0"))
k = -1
for name, mk in SHAPES.items():
    n = len(mk().Faces)
    for i in range(n):
        for off in (1.0, -1.0):
            for inter in (False, True):
                for join in (0, 2):
                    k += 1
                    if k < start:
                        continue
                    mode = ("I" if inter else "n") + "j%d" % join
                    tag = "%s_f%d_%+g_%s_j%d" % (name, i + 1, off, mode[0], join)
                    if MODES and mode not in MODES:
                        continue
                    os.write(2, ("CASE %d %s\n" % (k, tag)).encode())
                    s = make(mk)
                    sig = signature(s)
                    inloose = widest(s)  # a result may be as loose as its input
                    try:
                        r = s.makeThickness([s.Faces[i]], off, 1e-3, inter, False, 0, join)
                        p = []
                        if r.ShapeType not in ("Solid", "Compound"):
                            p.append(r.ShapeType)
                        if not r.isValid():
                            p.append("invalid")
                        sol = r.Solids
                        if not all(sh.isClosed() for x in sol for sh in x.Shells):
                            p.append("open")
                        gap = loose(r, inloose)[0] if not p else 0.0
                        st = "BAD:" + ",".join(p) if p else "LOOSE:%.3g" % gap if gap else "OK"
                        res = st + " vol=%.3f solids=%d shells=%d" % (r.Volume, len(sol), len(r.Shells))
                    except Exception as e:
                        text = str(e).strip()
                        res = "EXC " + (text.splitlines()[-1][:40] if text else type(e).__name__)
                    if signature(s) != sig:
                        res += " INPUT-CHANGED"
                    out("R %d %-28s %s" % (k, tag, res))
out("DONE")
os._exit(0)
