# mitre_exact.py: a straight fillet removed that mitres with the fillets beside it, the next
# fillet's offset passing over it (a convex fillet outward, a concave one inward): the thick
# solid built with booleans, against the kernel's.
#
# The wall is the closed offset of the part less the part (inward: the part less the offset).
# Beyond the removed cylinder, within its span between its two tangent lines, the wall is cut off
# flush -- but for the tubes round its tangent edges and the balls at their sharp ends, which
# stay. Where a tangent edge ends in a vertex at which all its faces are tangent (the mitre
# fading out) there is no ball: the tube ends flat.
#
# Env: SHAPES  names from shapes.py / shapes2.py
#      FACES   optional, "name:f,f;name:f" (1-based); default every cylinder face of the shape
#      T       thicknesses, default "0.25 0.5 0.75 1"
# A line a run: the two volumes and the volumes of the two differences; SAME or DIFFERENT.
import FreeCAD, Part, os, sys
P = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, P); sys.path.insert(0, os.path.join(P, "..", ".."))
from fix_level import from_env as _f
_f()
import shapes, shapes2
shapes.SHAPES.update(shapes2.SHAPES)
V = FreeCAD.Vector


def nrm(f, p):
    u, v = f.Surface.parameter(p)
    return f.normalAt(u, v)


def exact(s, fi, t):
    F = s.Faces[fi]
    cyl = F.Surface
    ax = cyl.Axis; C = cyl.Center; R = cyl.Radius
    tang = []
    for e in F.Edges:
        if type(e.Curve).__name__ != "Line":
            continue
        a, b = e.ParameterRange; q = e.valueAt((a + b) / 2)
        for k, g in enumerate(s.Faces):
            if k != fi and any(x.isSame(e) for x in g.Edges) and nrm(F, q).getAngle(nrm(g, q)) < 1e-3:
                tang.append(e)
    if len(tang) != 2:
        return None
    st = s.makeOffsetShape(t, 1e-7, False, False, 0, 0, False)
    if st.ShapeType != "Solid":
        st = Part.Solid(st.Shells[0])
    wall = st.cut(s) if t > 0 else s.cut(st)
    # what is beyond the cylinder: between its two tangent lines, as far out as the wall goes,
    # and along the axis a little past the face's ends
    rs = []
    for e in tang:
        a, b = e.ParameterRange; q = e.valueAt((a + b) / 2)
        d = q - C; d = d - ax * d.dot(ax); d.normalize(); rs.append(d)
    ps = [(v.Point - C).dot(ax) for v in F.Vertexes]
    lo = min(ps) - R - 2 * abs(t); length = max(ps) + R + 2 * abs(t) - lo
    c0 = C + ax * lo
    K = 200.
    mid = rs[0] + rs[1]; mid.normalize()
    poly = Part.makePolygon([c0, c0 + rs[0] * K, c0 + mid * (2 * K), c0 + rs[1] * K, c0])
    Z = Part.Face(poly).extrude(ax * length).common(
        Part.makeCylinder(R + 1.5 * abs(t), length, c0, ax)).cut(Part.makeCylinder(R, length, c0, ax))
    lips = []
    for e in tang:
        p0 = e.Vertexes[0].Point; p1 = e.Vertexes[1].Point
        lips.append(Part.makeCylinder(abs(t), (p1 - p0).Length, p0, p1 - p0))
        for v in e.Vertexes:
            ns = [nrm(g, v.Point) for g in s.Faces if any(w.isSame(v) for w in g.Vertexes)]
            if max(n.getAngle(ns[0]) for n in ns) > 1e-3:
                lips.append(Part.makeSphere(abs(t), v.Point))
    return wall.cut(Z.cut(lips[0].fuse(lips[1:])))


faces = {}
for item in os.environ.get("FACES", "").split(";"):
    if item:
        faces[item.split(":")[0]] = [int(x) - 1 for x in item.split(":")[1].split(",")]
for name in os.environ["SHAPES"].split():
    s = shapes.SHAPES[name]()
    for fi in faces.get(name, [i for i, f in enumerate(s.Faces)
                               if type(f.Surface).__name__ == "Cylinder"]):
        for t in [float(x) for x in os.environ.get("T", "0.25 0.5 0.75 1").split()]:
            try:
                ex = exact(s, fi, t)
            except Exception as e:
                ex = None
            if ex is None:
                print("Q %s f%d %+g no reference" % (name, fi + 1, t))
                continue
            try:
                r = s.makeThickness([s.Faces[fi]], t, 1e-7, False, False, 0, 0)
            except Exception:
                print("Q %s f%d %+g exact %.4f kernel REFUSED" % (name, fi + 1, t, ex.Volume))
                continue
            a = r.cut(ex).Volume; c = ex.cut(r).Volume
            print("Q %s f%d %+g exact %.4f kernel %.4f valid %s kernel-exact %.6f exact-kernel %.6f %s"
                  % (name, fi + 1, t, ex.Volume, r.Volume, r.isValid(), a, c,
                     "SAME" if a < 1e-4 and c < 1e-4 else "DIFFERENT"))
            sys.stdout.flush()
