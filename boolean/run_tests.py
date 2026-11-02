# Regression tests for the fork's fixes met through the general fuse and the
# booleans (BOPAlgo and what it calls).
#
# Run with any FreeCAD build linked against this OCCT:
#
#     FreeCADCmd tests/fork/boolean/run_tests.py
#
# Exit code is 0 when no case fails. See README.md for what each case covers;
# models/ has a C++ driver of each fix, run against an install.

import math
import os
import sys
import traceback

import FreeCAD as App
import Part

V = App.Vector
HERE = os.path.dirname(os.path.abspath(__file__))


def emit(line):
    # FreeCAD redirects sys.stdout into its own console, which swallows
    # script output under FreeCADCmd - write straight to fd 1.
    os.write(1, (line + "\n").encode())


# Every case here pins what the fork does. On another OCCT -- upstream's, as
# FreeCAD can load it -- they fail for want of the fork, so the suite says so
# and runs nothing. The fork is found as FreeCAD finds it, by a C function of
# its TKBRep; a FreeCAD from before Part.hasOCCTFunction runs the suite.
if hasattr(Part, "hasOCCTFunction") and not Part.hasOCCTFunction("TKBRep", "SetFuncShowTopoShape"):
    emit("SKIP: not the OCCT fork (TKBRep has no SetFuncShowTopoShape)")
    emit("summary: SKIP=1")
    sys.stdout.flush()
    os._exit(0)

results = []


def report(name, ok, what):
    results.append(ok)
    emit("%-44s %s  %s" % (name, "PASS" if ok else "FAIL", what))


def guarded(fix):
    # a fix's cases; an exception among them is a FAIL, not the end of the
    # suite (FreeCADCmd ends a script that raises with exit code 0)
    try:
        fix()
    except Exception:
        report(fix.__name__, False, "raised: " + traceback.format_exc().splitlines()[-1])


# #64: a cylinder (r 25, h 35) split by the plane y = k (z - 34.36), tilted
# off its axis, with a fuzzy value; the cylinder's seam at the cut (x = 25,
# y = 0) or turned 90 deg away. Two valid solids each time; with the seam
# away, each within 1% of its volume at no fuzzy value. (With the seam at
# the cut a fuzzy value merges the plane's crossing of the top rim into the
# seam's vertex there, valid within tolerances but read short by the volume
# integrals: only the two valid solids are asked. README.md, #64.)
def split(k, fuzzy, angle):
    cyl = Part.makeCylinder(25, 35)
    cyl.rotate(V(), V(0, 0, 1), angle)
    zc = 34.36
    pts = [V(-40, k * (-5 - zc), -5), V(-40, k * (40 - zc), 40), V(40, k * (40 - zc), 40),
           V(40, k * (-5 - zc), -5)]
    plane = Part.Face(Part.makePolygon(pts + pts[:1]))
    res = cyl.generalFuse([plane], fuzzy)[0]
    return res if res.isValid() else None, sorted(s.Volume for s in res.Solids)


def issue064():
    for k in (0.1, 0.35, 1.0):
        for angle in (0, 90):
            ref = split(k, 0.0, angle)[1]
            for fuzzy in (0.0, 0.1, 0.5, 1.0):
                res, vols = split(k, fuzzy, angle)
                ok = res is not None and len(vols) == 2 and len(ref) == 2
                if ok and not (angle == 0 and fuzzy > 0):
                    ok = all(abs(v - r) <= 1e-2 * r for v, r in zip(vols, ref))
                report("issue064_k%g_seam%d_fuzzy%g" % (k, angle, fuzzy), ok,
                       ("invalid " if res is None else "") + " ".join("%.4f" % v for v in vols))


guarded(issue064)


# #580: #580's Pad003, whose planar face 19 holds a degenerated edge with no
# 3D curve, mirrored and moved with a copy, and fused with its mirror: each
# valid, the copies of its volume, the fuse twice it less the common. The
# copy used to drop that edge's pcurve (README.md, #580).
def solid_case(name, shape, want):
    ok = shape.isValid() and abs(shape.Volume - want) <= 1e-6 * want
    invalid = "" if shape.isValid() else "invalid "
    report(name, ok, "%svol %.4f (want %.4f)" % (invalid, shape.Volume, want))


def issue580():
    pad = Part.read(os.path.join(HERE, "models", "issue580_pad003.brep"))
    v0 = pad.Volume
    mirrored = pad.mirror(V(0, 0, 0), V(0, 1, 0))
    solid_case("issue580_mirror", mirrored, v0)
    moved = pad.copy()
    move = App.Placement(V(1, 2, 3), App.Rotation(V(1, 0, 0), math.degrees(0.7))).toMatrix()
    moved.transformShape(move, True)
    solid_case("issue580_moved_copy", moved, v0)
    solid_case("issue580_fuse_mirror", pad.fuse(mirrored), 2 * v0 - pad.common(mirrored).Volume)


guarded(issue580)

# #613: a cylinder's or a cone's face, a whole turn with its seam d off
# u = 0, cut by the plane z = 0: the section is the whole circle. With the
# seam's vertex within tolerance of the circle's end (d 1e-8, 2e-8) the
# section was empty (README.md, #613).
def seam_surface(kind):
    if kind == "cylinder":
        s = Part.Cylinder()
        s.Radius = 21.2
    else:
        s = Part.Cone()
        s.SemiAngle = 0.2
        s.Radius = 21.2
    s.Center = V(0, 0, -5)
    s.Axis = V(0, 0, 1)
    return s


def issue613():
    for kind, want in (("cylinder", 2 * math.pi * 21.2),
                       ("cone", 2 * math.pi * (21.2 + 5 * math.tan(0.2)))):
        surf = seam_surface(kind)
        for d in (0.0, 1e-9, 1e-8, 2e-8, 5e-8, 1e-6):
            face = surf.toShape(d, d + 2 * math.pi, 0.0, 10.0)
            plane = Part.makePlane(100, 100, V(-50, -50, 0))
            sec = face.section(plane)
            length = sum(e.Length for e in sec.Edges)
            ok = sec.Edges and abs(length - want) <= 1e-6 * want
            report("issue613_%s_seam_%g" % (kind, d), bool(ok),
                   "%d edge(s), length %.6f (want %.6f)" % (len(sec.Edges), length, want))


guarded(issue613)

# A box under a B-spline dome, the dome's four edges filleted (r 3): the
# offsets (-2) of two fillets meeting in a mitre at a corner of the dome,
# each made alone, cut each other in one edge. Both meet the dome
# tangentially there, so the offsets are tangent at the corner's offset; the
# section passed the corner at a hair's distance and ended outside one of
# them -- no vertex there, no edge (README.md, "A section's tangent end at a
# corner").
def dome_tangent_corner():
    dome = Part.Shape()
    dome.importBrep(os.path.join(HERE, "models", "dome_fillet_r3.brep"))
    for i, j in ((3, 8), (3, 10), (7, 8), (7, 10)):
        o1 = dome.Faces[i - 1].makeOffsetShape(-2, 1e-7)
        o2 = dome.Faces[j - 1].makeOffsetShape(-2, 1e-7)
        sec = o1.section(o2)
        length = sum(e.Length for e in sec.Edges)
        ok = len(sec.Edges) == 1 and abs(length - 1.7038) <= 1e-3 * 1.7038
        report("dome_tangent_corner_mitre_%dx%d" % (i, j), ok,
               "%d edge(s), length %.4f (want 1.7038)" % (len(sec.Edges), length))


guarded(dome_tangent_corner)


# #617: the pad's two prisms on the cut of the revolution by z = 0 -- degree
# 8 B-splines of 29 spans, the knots bunched where the cut turns. The volume
# and area integrals gave a point or two a span: 92341 for 71191. Held
# against what does not come from them: each lobe's area by the shoelace
# over a dense polygon of its curve, the curve's length (README.md, "#617: a
# volume integrated a point or two a span").
def issue617_gprop():
    prisms = Part.Shape()
    prisms.importBrep(os.path.join(HERE, "models", "issue617_prisms.brep"))
    vol, area = 0.0, 0.0
    for solid in prisms.Solids:
        top = max(solid.Faces, key=lambda f: f.CenterOfMass.z)
        edge = top.OuterWire.Edges[0]
        pts = edge.discretize(Number=200001)
        lobe = 0.5 * abs(sum(p.x * q.y - q.x * p.y for p, q in zip(pts, pts[1:] + pts[:1])))
        height = top.CenterOfMass.z - min(f.CenterOfMass.z for f in solid.Faces)
        vol += lobe * height
        area += 2 * lobe + edge.Length * height
    ok = (len(prisms.Solids) == 2 and abs(prisms.Volume - vol) <= 1e-7 * vol
          and abs(prisms.Area - area) <= 1e-7 * area)
    report("issue617_gprop_bspline_prisms", ok, "vol %.4f (want %.4f), area %.4f (want %.4f)"
           % (prisms.Volume, vol, prisms.Area, area))


guarded(issue617_gprop)


# A prism on an ellipse (height 8) offset by d with the Intersection join:
# its wall the offset surface of the prism's, its caps planes. The volume
# and area integrals of an offset took one rule of 18 points over the turn,
# 0.08% to 18% off as the ellipse narrows. Held against Steiner: the offset
# region pi a b + L d + pi d^2, its curve L + 2 pi d, L the ellipse's length
# (README.md, "An offset surface integrated at 18 points").
def offset_surface_gprop():
    for a, b, d in ((10, 5, 1), (10, 5, -1), (10, 2, 1), (6, 5, 1), (10, 1, 1), (30, 1, 1)):
        base = Part.Face(Part.Wire(Part.Ellipse(V(0, 0, 0), a, b).toShape()))
        solid = base.extrude(V(0, 0, 8)).makeOffsetShape(d, 1e-7, join=2)
        # the ellipse's length: the trapezoid sum of a periodic integrand
        n = 4000
        ts = [2 * math.pi * k / n for k in range(n)]
        length = sum(math.hypot(a * math.sin(t), b * math.cos(t)) for t in ts) * 2 * math.pi / n
        region = math.pi * a * b + length * d + math.pi * d * d
        vol, area = region * (8 + 2 * d), 2 * region + (length + 2 * math.pi * d) * (8 + 2 * d)
        walls = [f for f in solid.Faces if f.Surface.__class__.__name__ == "OffsetSurface"]
        ok = (solid.isValid() and len(walls) == 1 and abs(solid.Volume - vol) <= 1e-7 * vol
              and abs(solid.Area - area) <= 1e-7 * area)
        report("offset_surface_gprop_%gx%g_%+g" % (a, b, d), ok,
               "vol %.6f (want %.6f), area %.6f (want %.6f)"
               % (solid.Volume, vol, solid.Area, area))


guarded(offset_surface_gprop)


# A prism on an ellipse (height 8), and spheroids, half an ellipse revolved
# about its axis: the area element of an extrusion or a revolution carries
# the curve's speed under a square root, one rule of 18 points over the
# turn: 1.8e-5 to 0.45% off. Held against closed forms (README.md, "An
# ellipse's extrusion: its area integrated at 18 points").
def ellipse_length(a, b, n=4000):
    ts = [2 * math.pi * k / n for k in range(n)]
    return sum(math.hypot(a * math.sin(t), b * math.cos(t)) for t in ts) * 2 * math.pi / n


def extrusion_area_gprop():
    for a, b in ((10, 5), (10, 2), (6, 5), (10, 1), (30, 1)):
        base = Part.Face(Part.Wire(Part.Ellipse(V(0, 0, 0), a, b).toShape()))
        solid = base.extrude(V(0, 0, 8))
        vol, area = 8 * math.pi * a * b, 2 * math.pi * a * b + 8 * ellipse_length(a, b)
        ok = abs(solid.Volume - vol) <= 1e-9 * vol and abs(solid.Area - area) <= 1e-9 * area
        report("extrusion_area_gprop_prism_%gx%g" % (a, b), ok, "area %.6f (want %.6f), vol %.6f"
               % (solid.Area, area, solid.Volume))
    # a across the axis, c along it
    for a, c in ((10, 2), (10, 5), (2, 10), (5, 10)):
        if a > c:
            ell, t1, t2 = Part.Ellipse(V(a, 0, 0), V(0, 0, c), V(0, 0, 0)), -math.pi / 2, math.pi / 2
            e = math.sqrt(1 - c * c / (a * a))
            area = 2 * math.pi * a * a + math.pi * c * c / e * math.log((1 + e) / (1 - e))
        else:
            ell, t1, t2 = Part.Ellipse(V(0, 0, c), V(a, 0, 0), V(0, 0, 0)), 0, math.pi
            e = math.sqrt(1 - a * a / (c * c))
            area = 2 * math.pi * a * a * (1 + c / (a * e) * math.asin(e))
        arc = ell.toShape(t1, t2)
        p1, p2 = arc.Vertexes[0].Point, arc.Vertexes[-1].Point
        face = Part.Face(Part.Wire([arc, Part.makeLine(p2, p1)]))
        solid = Part.Solid(Part.Shell(face.revolve(V(0, 0, 0), V(0, 0, 1), 360).Faces))
        vol = 4 / 3 * math.pi * a * a * c
        ok = abs(abs(solid.Volume) - vol) <= 1e-9 * vol and abs(solid.Area - area) <= 1e-9 * area
        report("extrusion_area_gprop_spheroid_%gx%g" % (a, c), ok,
               "area %.6f (want %.6f), vol %.6f (want %.6f)" % (solid.Area, area, abs(solid.Volume), vol))


guarded(extrusion_area_gprop)

failed = results.count(False)
emit("---")
emit("summary: PASS=%d%s" % (results.count(True), "  FAIL=%d" % failed if failed else ""))
sys.stdout.flush()
os._exit(1 if failed else 0)
