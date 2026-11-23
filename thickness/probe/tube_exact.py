# tube_exact.py: the tube with its two top edges filleted (shapes.py "tube_fillet", fillets of
# radius 1), a face beside a fillet removed inward by t > 1: the thick solid built with booleans,
# against the kernel's. The fillet's offset is turned inside out at t > 1 and no face of the wall.
#
# The wall is the part less the cavity, the cavity revolved from its profile in the plane y = 0:
#   f1 / f5 (outer / inner cylinder): between the offsets of the bottom, the top and the other
#     cylinder, open through the removed face, less the tube of radius t round the removed
#     face's tangent edge (the circle at z = 11).
#   f4 (top): the tubes round its two edges, 2 apart, pass through each other: the cavity is
#     closed, under the two tubes, and the wall has it for a void.
#
# Env: RUNS  "face:t face:t ...", face one of 1 4 5, t > 1; default "1:1.05 4:1.05 5:1.05"
#      NPTS  random points in the tube's box compared, default 4000
# A line a run: the two volumes, the shells, the points that differ; SAME or DIFFERENT.
import FreeCAD, Part, os, sys, math, random
P = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, P); sys.path.insert(0, os.path.join(P, "..", ".."))
from fix_level import from_env as _f
_f()
import shapes
V = FreeCAD.Vector
s = shapes.SHAPES["tube_fillet"]()


def p(r, z):
    return V(r, 0, z)


def arc(c, t, a0, a1):
    def q(a):
        return p(c[0] + t * math.cos(a), c[1] + t * math.sin(a))
    return Part.Arc(q(a0), q((a0 + a1) / 2), q(a1)).toShape()


def below(y, x):
    """The angle of (x, y), y < 0, in (-pi, 0)."""
    return math.atan2(y, x)


def cavity(fi, t):
    w = math.sqrt(2 * t - 1)       # how far from its edge a tube of radius t is t - 1 deep
    if fi == 4:
        h = math.sqrt(t * t - 1)   # the two tubes meet at r = 8, h under the top
        ro, ri = 10 - t, 6 + t
        es = [Part.makeLine(p(ri, t), p(ro, t)), Part.makeLine(p(ro, t), p(ro, 12 - w)),
              arc((9, 12), t, below(-w, ro - 9), below(-h, -1.)),
              arc((7, 12), t, below(-h, 1.), below(-w, ri - 7)),
              Part.makeLine(p(ri, 12 - w), p(ri, t))]
    else:
        rc, rf, sg = (10., 6 + t, -1.) if fi == 1 else (6., 10 - t, 1.)
        es = [Part.makeLine(p(rc, t), p(rf, t)), Part.makeLine(p(rf, t), p(rf, 12 - t)),
              Part.makeLine(p(rf, 12 - t), p(rc + sg * w, 12 - t)),
              arc((rc, 11), t, below(-(t - 1), sg * w), -math.pi / 2),
              Part.makeLine(p(rc, 11 - t), p(rc, t))]
    return Part.Face(Part.Wire(es)).revolve(V(0, 0, 0), V(0, 0, 1), 360)


random.seed(7)
pts = [V(random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(0, 12))
       for i in range(int(os.environ.get("NPTS", "4000")))]
for item in os.environ.get("RUNS", "1:1.05 4:1.05 5:1.05").split():
    fi, t = item.split(":"); fi = int(fi); t = float(t)
    ex = s.cut(cavity(fi, t))
    try:
        r = s.makeThickness([s.Faces[fi - 1]], -t, 1e-7, False, False, 0, 0)
    except Exception:
        print("Q tube_fillet f%d -%g exact %.4f kernel REFUSED" % (fi, t, ex.Volume))
        continue
    # a point within 1e-6 of either boundary is on it, and counted on neither side
    diff = [q for q in pts if r.isInside(q, 1e-7, True) != ex.isInside(q, 1e-7, True)
            and Part.Vertex(q).distToShape(r.Shells[0])[0] > 1e-6
            and min(Part.Vertex(q).distToShape(sh)[0] for sh in ex.Shells + r.Shells) > 1e-6]
    same = not diff and abs(ex.Volume - r.Volume) < 1e-3
    print("Q tube_fillet f%d -%g exact %.4f kernel %.4f valid %s shells %d points differ %d of %d %s%s"
          % (fi, t, ex.Volume, r.Volume, r.isValid(), len(r.Shells), len(diff), len(pts),
             "SAME" if same else "DIFFERENT", "" if not diff else " first %s" % diff[0]))
    sys.stdout.flush()
