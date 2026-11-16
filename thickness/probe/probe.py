# probe.py -- plain shapes with blends (shapes.py), every face removed in turn,
# 0.5 and 1 either way (README.md sec 78). One shape a run:
#   SHAPE  its name in shapes.py      OUT    the file the lines go to
#   JOINS  "0 2" (Arc, Intersection)   TOL    the thickness' tolerance, 1e-7
#   N      points an Arc result is read by, 400 (0: not read)
#   SKIP   "tag;tag": runs to leave out (one that does not return)
#   SET    2: the shapes of shapes2.py     INTER  1: with every pair of faces intersected
# An Arc result is read by random points in the shape's box: in the wall where
# on the right side of the part and nearer than the thickness to a face that
# stays. Not read: at an edge of the removed face its neighbour stands at an
# angle to (the wall ends flush there), and beyond the removed face's surface
# unless the nearest kept point is on a tangent edge of it (the tubes' lips).
# The shape is made anew for every run and compared with itself after it.
import FreeCAD, Part, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapes import SHAPES
if os.environ.get("SET", "") == "2":
    from shapes2 import SHAPES
V = FreeCAD.Vector


def beyond(face, p):
    """Whether p lies on the outer side of the face's surface, carried on."""
    try:
        u, v = face.Surface.parameter(p)
        return (p - face.Surface.value(u, v)).dot(face.normalAt(u, v)) > 1e-9
    except Exception:
        return False


name = os.environ["SHAPE"]
joins = [int(x) for x in os.environ.get("JOINS", "0 2").split()]
n = int(os.environ.get("N", "400"))
TOL = float(os.environ.get("TOL", "1e-7"))
INTER = os.environ.get("INTER", "") == "1"
s = SHAPES[name]()


def deep(s):
    """What a run must leave as it found it: every edge of every face with its range, tolerance
    and pcurve's ends, the vertices (as many as there are, each with its tolerance), validity."""
    sig = []
    for f in s.Faces:
        for w in f.Wires:
            for e in w.Edges:
                c = f.curveOnSurface(e)
                pc = "none" if c is None else "%.6f %.6f %.5f %.5f %.5f %.5f" % (
                    c[1], c[2], c[0].value(c[1]).x, c[0].value(c[1]).y, c[0].value(c[2]).x,
                    c[0].value(c[2]).y)
                kind = "degenerated" if e.Degenerated else type(e.Curve).__name__
                sig.append("%s %.6f %.6f %.3g %s %s" % (kind, e.FirstParameter,
                                                        e.LastParameter, e.Tolerance,
                                                        e.Orientation, pc))
    sig.append(" ".join("%.3g" % v.Tolerance for v in s.Vertexes))
    sig.append("%s %.6f %d %d" % (s.isValid(), s.Volume, len(s.Edges), len(s.Faces)))
    return sig


skip = set(x.strip() for x in os.environ.get("SKIP", "").split(";") if x.strip())
out = open(os.environ["OUT"], "w")
out.write("# %s faces %d valid %s vol %.4f\n" % (name, len(s.Faces), s.isValid(), s.Volume))
out.flush()
solid = s.Solids[0]


def read(r, fi, t):
    rem = s.Faces[fi]
    kept = Part.Compound([f for i, f in enumerate(s.Faces) if i != fi])
    sharp = []
    for e in rem.Edges:
        for k, g in enumerate(s.Faces):
            if k == fi or not any(x.isSame(e) for x in g.Edges):
                continue
            a, b = e.ParameterRange
            q = e.valueAt((a + b) / 2)
            try:
                n1 = rem.normalAt(*rem.Surface.parameter(q))
                n2 = g.normalAt(*g.Surface.parameter(q))
                if n1.getAngle(n2) > 0.2:
                    sharp.append(e)
            except Exception:
                pass
    smooth = [e for e in rem.Edges if not any(e.isSame(x) for x in sharp)]
    smooth = Part.Compound(smooth) if smooth else None
    sharp = Part.Compound(sharp) if sharp else None
    bb = s.BoundBox
    m = abs(t) + 0.5
    random.seed(11)
    bad = used = tries = 0
    first = ""
    rsols = r.Solids
    while used < n and tries < 60 * n:
        tries += 1
        p = V(random.uniform(bb.XMin - m, bb.XMax + m), random.uniform(bb.YMin - m, bb.YMax + m),
              random.uniform(bb.ZMin - m, bb.ZMax + m))
        v = Part.Vertex(p)
        d = kept.distToShape(v)[0]
        if d > abs(t) + 0.3 or abs(d - abs(t)) < 0.03 or d < 0.03 or rem.distToShape(v)[0] < 0.03:
            continue
        if sharp is not None and abs(sharp.distToShape(v)[0] - d) < 1e-6:
            continue
        # beyond the removed face's surface the wall is cut off flush, but for the lips of the
        # tubes round its tangent edges: read there only where the nearest kept point is on one
        on_lip = smooth is not None and abs(smooth.distToShape(v)[0] - d) < 1e-6
        if t > 0 and beyond(rem, p) and not on_lip:
            continue
        inside = solid.isInside(p, 1e-6, True)
        want = (not inside and d < abs(t)) if t > 0 else (inside and d < abs(t))
        got = any(x.isInside(p, 1e-6, True) for x in rsols)
        used += 1
        if want != got:
            bad += 1
            if not first:
                first = " first (%.3f %.3f %.3f) kept %.3f want %s" % (p.x, p.y, p.z, d, want)
    return "points %d wrong %d%s" % (used, bad, first)


for fi in range(len(s.Faces)):
    for join in joins:
        for t in (0.5, -0.5, 1.0, -1.0):
            tag = "%s f%d %+g j%d" % (name, fi + 1, t, join)
            if tag in skip:
                out.write("%s | %s | HANG (skipped)\n" % (tag, type(s.Faces[fi].Surface).__name__))
                out.flush()
                continue
            s = SHAPES[name]()
            solid = s.Solids[0]
            before = deep(s)
            try:
                r = s.makeThickness([s.Faces[fi]], t, TOL, INTER, False, 0, join)
                if not r.isValid():
                    res = "INVALID vol %.4f" % r.Volume
                else:
                    res = "valid solids %d vol %.4f" % (len(r.Solids), r.Volume)
                    if join == 0 and n > 0:
                        res += " " + read(r, fi, t)
            except Exception as e:
                res = "REFUSED"
            if deep(s) != before:
                res += " INPUT-CHANGED"
            out.write("%s | %s | %s\n" % (tag, type(s.Faces[fi].Surface).__name__, res))
            out.flush()
out.write("# done\n"); out.close()
