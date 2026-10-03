# FreeCADCmd build.py -- the exact Arc-join answer, outward, for the half ball
# in two domes with the dome z > 0 removed (Thickness.md sec 23 and 25,
# sweep/onedome.py "out, j0"), built from primitives: $OUT/arc_out.brep, a
# valid solid of 89.1639 with twelve faces, two of them the slivers.
import os, math
import FreeCAD as App, Part
V = App.Vector
def emit(s): os.write(1, (s + "\n").encode())
R, t, BIG = 5.0, 0.5, 40.0
def box(x0, y0, z0, x1, y1, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
ball, ballt = Part.makeSphere(R), Part.makeSphere(R + t)
lowy = box(-BIG, 0, -BIG, BIG, BIG, 0)          # y >= 0, z <= 0
slab_lo = box(-BIG, -t, -BIG, BIG, 0, 0)         # the flat's slab, z <= 0
slab_hi = box(-BIG, -t, 0, BIG, 0, BIG)          # the flat's slab, z >= 0
A = ballt.cut(ball).common(lowy)                 # the kept dome's offset
B = Part.makeCylinder(R, t, V(0, -t, 0), V(0, 1, 0)).fuse(
    Part.makeTorus(R, t, V(), V(0, 1, 0))).common(slab_lo)   # the flat's slab and the quarter tube round its rim
C = ball.common(slab_hi)                         # the flat's slab beside the removed dome, cut by the sphere
D = Part.makeSphere(t, V(R, 0, 0)).fuse(Part.makeSphere(t, V(-R, 0, 0))).common(box(-BIG, -BIG, 0, BIG, 0, BIG))  # a ball round each end
E = Part.makeTorus(R, t, V(), V(0, 0, 1)).common(box(-BIG, 0, 0, BIG, BIG, BIG)).cut(ball)  # the tube round the equator
s = A.fuse([B, C, D, E])
emit("fused: valid %s solids %d volume %.4f" % (s.isValid(), len(s.Solids), s.Volume))
r = s.removeSplitter()
emit("refined: valid %s solids %d faces %d volume %.4f (hand 89.1638)" % (r.isValid(), len(r.Solids), len(r.Faces), r.Volume))
small = sorted(r.Faces, key=lambda f: f.Area)[:6]
for f in small:
    c = f.CenterOfMass; bb = f.BoundBox
    emit("face %-10s area %.3e centre (%.4f %.4f %.4f) size %.4f x %.4f x %.4f edges %d" % (
        f.Surface.__class__.__name__, f.Area, c.x, c.y, c.z, bb.XLength, bb.YLength, bb.ZLength, len(f.Edges)))
r.exportBrep(os.environ["OUT"] + "/arc_out.brep")
emit("DONE")
