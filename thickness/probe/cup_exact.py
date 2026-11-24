# cup_exact.py: the revolved cup (shapes2.py "revolve_cup"), its floor (face 5) removed inward by t:
# the thick solid built with booleans, against the kernel's (README.md sec 107).
#
# The wall is the part less the cavity, the cavity revolved from its profile in the plane y = 0:
# deeper than t from the bottom and from the outer side, and either under the floor's plane
# (z < 2: the inner side's wall ends there, cut off flush by the floor's plane) or deeper than t
# from the inner side and the top. The wall is 1.887 thick at its foot and 1.955 at its rim: up
# to 0.94 the cavity runs up the wall, from 0.98 it is the pocket under the floor alone, and
# between the wall keeps a void of its own above the pocket.
#
# Env: TS    thicknesses, default "0.5 0.9 0.96 1 1.5"
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
    """The half plane (as a big face in the plane y = 0) to the left of p->q moved t to the left."""
    d = V(q[0] - p[0], 0, q[1] - p[1]); d.normalize(); n = V(-d.z, 0, d.x)
    a = V(p[0], 0, p[1]) + n * t - d * BIG; b = a + d * 2 * BIG
    return Part.Face(Part.makePolygon([a, b, b + n * BIG, a + n * BIG, a]))
def rev(f):
    return f.revolve(V(0, 0, 0), V(0, 0, 1), 360)
def cavity(t):
    right = Part.Face(Part.makePolygon([V(0, 0, -BIG), V(BIG, 0, -BIG), V(BIG, 0, BIG), V(0, 0, BIG), V(0, 0, -BIG)]))
    bottom = half((0, 0), (12, 0), t)          # above z = t
    outer = half((12, 0), (15, 14), t)         # inside the outer cone by t
    inner = half((13, 14), (10.5, 2), t)       # outside the inner cone by t
    top = half((15, 14), (13, 14), t)          # below z = 14 - t
    under = half((0, 2), (20, 2), 0)           # z < 2 ... left of (0,2)->(20,2) is z > 2
    base = right.common(bottom).common(outer)
    a = base.cut(under)                         # under the floor
    b = base.common(inner).common(top)
    f = a.fuse(b)
    return [rev(x) for x in f.Faces]
random.seed(3)
pts = [V(random.uniform(-15, 15), random.uniform(-15, 15), random.uniform(0, 14)) for i in range(int(os.environ.get("NPTS", "6000")))]
for t in [float(x) for x in os.environ.get("TS", "0.5 0.9 0.96 1 1.5").split()]:
    ex = s
    for c in cavity(t):
        ex = ex.cut(c)
    line = "Q cup f5 -%g exact %.4f valid %s solids %d shells %d" % (t, ex.Volume, ex.isValid(), len(ex.Solids), len(ex.Shells))
    try:
        r = s.makeThickness([s.Faces[4]], -t, 1e-7, False, False, 0, 0)
        diff = [q for q in pts if r.isInside(q, 1e-7, True) != ex.isInside(q, 1e-7, True)]
        line += " | kernel %.4f valid %s shells %d points differ %d of %d" % (r.Volume, r.isValid(), len(r.Shells), len(diff), len(pts))
        if diff: line += " first (%.3f %.3f %.3f) r %.3f" % (diff[0].x, diff[0].y, diff[0].z, math.hypot(diff[0].x, diff[0].y))
    except Exception:
        line += " | kernel REFUSED"
    print(line); sys.stdout.flush()
