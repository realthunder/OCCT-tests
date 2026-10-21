# The vertex-on-its-curve check shared by the suites and sweeps.
#
# An edge's 3D curve, at the ends of its parameter range, must meet the
# edge's vertices. BRepCheck measures that gap against the vertex's
# tolerance, so a vertex raised to cover it passes: x16win's chamfer at a
# corner of two fillets (fillet/README.md) left three edges whose curves stop
# 0.3819 short of their vertices, at edge tolerance 2.2e-4, the vertices
# raised to 0.382 -- valid, BOP's check clean, and the volume 45.6 out.
#
# A vertex may legitimately sit farther from one of its edges than that
# edge's own tolerance (it grows to take in every edge it ends), so the
# check allows ten times the edge's tolerance, and 1e-4 at least -- the
# accuracy ChFi3d works to (its tolesp and tolapp3d), below which #876's and
# #962's corners came out 1.3e-5 and 4.8e-5 off. A caller that accepts a
# looser result passes how loose (a fillet a few thousandths wide on #876's
# edge a degree from smooth ends in one vertex for both its lines, 0.0026
# from each), and a result may be as loose as its input (case 5829's fillet,
# made while a plate was held tangent whatever it missed, has two walls
# meeting 0.38 from their vertex, and its thickness keeps them).
import math


def loose(shape, allowed=0.0):
    """The largest curve-end gap past max(10 x its edge's tolerance, 1e-4,
    <allowed>), with its edge's index; (0, 0) when there is none."""
    worst = (0.0, 0)
    for i, e in enumerate(shape.Edges, 1):
        a, b = e.ParameterRange
        # an unbounded edge (a document's axis, +-2e100 and no vertex) has no
        # end to check
        if e.Degenerated or not e.Vertexes or math.isinf(a) or math.isinf(b):
            continue
        ends = ((e.valueAt(a), e.firstVertex(False)), (e.valueAt(b), e.lastVertex(False)))
        for p, v in ends:
            gap = (p - v.Point).Length
            if gap > max(10 * e.Tolerance, 1e-4, allowed) and gap > worst[0]:
                worst = (gap, i)
    return worst


def widest(shape):
    """The largest gap between any edge's curve end and its vertex, however
    loose the edge: what a result made from <shape> may keep of it (case
    5829's walls meet 0.38 from their vertex on edges loose enough to cover
    it; the thickness's new edges are not, and the gap shows there)."""
    worst = 0.0
    for e in shape.Edges:
        a, b = e.ParameterRange
        if e.Degenerated or not e.Vertexes or math.isinf(a) or math.isinf(b):
            continue
        for p, v in ((e.valueAt(a), e.firstVertex(False)), (e.valueAt(b), e.lastVertex(False))):
            worst = max(worst, (p - v.Point).Length)
    return worst
