# cup_bottom_exact.py: the revolved cup (shapes2.py "revolve_cup"), its bottom (face 1) removed
# inward by t: the thick solid built with booleans, against the kernel's (README.md sec 108; the
# floor is cup_exact.py).
#
# The wall is the part less the cavity, the cavity revolved from its profile in the plane y = 0:
# deeper than t from the outer side and the top, and further than t from the cup's inside -- the
# floor and the inner side, with a round of t about the edge between them.
#
# Env: TS    thicknesses, default "0.5 0.9 1 1.2 1.5"
#      NPTS  random points in the cup's box compared, default 6000
# A line a run: the two volumes, the shells, the points that differ.
import FreeCAD, Part, os, sys, math, random
P = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, P); sys.path.insert(0, os.path.join(P, "..", ".."))
from fix_level import from_env as _f
_f()
import shapes2
V = FreeCAD.Vector
s = shapes2.SHAPES["revolve_cup"]()
BIG = 60.
def half(p, q, t):
    d = V(q[0] - p[0], 0, q[1] - p[1]); d.normalize(); n = V(-d.z, 0, d.x)
    a = V(p[0], 0, p[1]) + n * t - d * BIG; b = a + d * 2 * BIG
    return Part.Face(Part.makePolygon([a, b, b + n * BIG, a + n * BIG, a]))
def cavity(t):
    right = Part.Face(Part.makePolygon([V(0, 0, -BIG), V(BIG, 0, -BIG), V(BIG, 0, BIG), V(0, 0, BIG), V(0, 0, -BIG)]))
    outer = half((12, 0), (15, 14), t)
    top = half((15, 14), (13, 14), t)
    k = 2.5 / 12.
    air = Part.Face(Part.makePolygon([V(-30, 0, 2), V(10.5, 0, 2), V(10.5 + k * 38, 0, 40), V(-30, 0, 40), V(-30, 0, 2)]))
    # the inside grown by t, round at its corner: the union of the inside, a strip along each
    # side and a disc at the corner
    d = V(k, 0, 1); d.normalize(); n = V(d.z, 0, -d.x)
    c = V(10.5, 0, 2); e = V(10.5 + k * 38, 0, 40)
    grown = air.fuse(Part.Face(Part.makePolygon([V(-30, 0, 2), V(-30, 0, 2 - t), V(10.5, 0, 2 - t), c, V(-30, 0, 2)])))
    grown = grown.fuse(Part.Face(Part.makePolygon([c, c + n * t, e + n * t, e, c])))
    grown = grown.fuse(Part.Face(Part.Wire(Part.makeCircle(t, c, V(0, 1, 0)))))
    f = right.common(outer).common(top).cut(grown)
    return [x.revolve(V(0, 0, 0), V(0, 0, 1), 360) for x in f.Faces]
random.seed(3)
pts = [V(random.uniform(-15, 15), random.uniform(-15, 15), random.uniform(0, 14)) for i in range(int(os.environ.get("NPTS", "6000")))]
for t in [float(x) for x in os.environ.get("TS", "0.5 0.9 1 1.2 1.5").split()]:
    ex = s
    for c in cavity(t):
        ex = ex.cut(c)
    line = "Q cup f1 -%g exact %.4f valid %s shells %d" % (t, ex.Volume, ex.isValid(), len(ex.Shells))
    try:
        r = s.makeThickness([s.Faces[0]], -t, 1e-7, False, False, 0, 0)
        diff = [q for q in pts if r.isInside(q, 1e-7, True) != ex.isInside(q, 1e-7, True)]
        line += " | kernel %.4f valid %s shells %d points differ %d of %d" % (r.Volume, r.isValid(), len(r.Shells), len(diff), len(pts))
        if diff: line += " first (%.3f %.3f %.3f) r %.3f" % (diff[0].x, diff[0].y, diff[0].z, math.hypot(diff[0].x, diff[0].y))
    except Exception:
        line += " | kernel REFUSED"
    print(line); sys.stdout.flush()
