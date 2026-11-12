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


# #617: the pad's prisms and the revolution they stand on. The revolution's
# profile is a closed B-spline, not periodic, and the prisms' bottom edges --
# its cut by z = 0 -- start and end on its seam circle. Their pcurves on it
# ran back across the whole v range on the last step (the trap guard's fresh
# search took the bound the walk had not come to) and were approximated in 16
# segments, too few for 29 spans: every general fuse of the two carried an
# edge of tolerance 36 to 39, and the plain one took 184 s (README.md, "#617:
# the pad's bottom edge projected across the revolution's seam").
def issue617_seam_pcurve():
    for fuzzy in (0.0, 1e-5):
        rev = Part.Shape()
        rev.importBrep(os.path.join(HERE, "models", "issue617_revolution.brep"))
        prisms = Part.Shape()
        prisms.importBrep(os.path.join(HERE, "models", "issue617_prisms.brep"))
        res, _ = rev.generalFuse([prisms], fuzzy)
        tol = max(e.Tolerance for e in res.Edges)
        report("issue617_seam_pcurve_fuzzy%g" % fuzzy, tol <= 1e-3,
               "largest edge tolerance %.3g (want <= 1e-3), %d edges" % (tol, len(res.Edges)))


guarded(issue617_seam_pcurve)


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


# A B-spline integrated across its knots: an ellipse's exact rational
# B-spline (four quarters, its knots C1) -- the rule of an edge on it, or of
# the face it is extruded or revolved from, ran across the knots: 1e-3 off.
# Held against closed forms (README.md, "A B-spline integrated across its
# knots").
def bspline_ellipse(a, b, quarters=4, periodic=False, plane="xy", knots=None):
    w = math.sqrt(0.5)
    pts = [(a, 0), (a, b), (0, b), (-a, b), (-a, 0), (-a, -b), (0, -b), (a, -b), (a, 0)]
    pts = pts[: 2 * quarters + 1]
    weights = [1 if i % 2 == 0 else w for i in range(len(pts))]
    if plane == "xy":
        poles = [V(x, y, 0) for x, y in pts]
    else:  # xz, from -z to +z about x >= 0 for a half
        poles = [V(y, 0, -x) for x, y in pts]
    knots = knots or list(range(quarters + 1))
    curve = Part.BSplineCurve()
    if periodic:
        curve.buildFromPolesMultsKnots(poles[:-1], [2] * (quarters + 1), knots, True, 2,
                                       weights[:-1])
    else:
        curve.buildFromPolesMultsKnots(poles, [3] + [2] * (quarters - 1) + [3], knots, False, 2,
                                       weights)
    return curve


def bspline_knots_gprop():
    def check(name, solid, vol, area):
        ok = abs(abs(solid.Volume) - vol) <= 1e-9 * vol and abs(solid.Area - area) <= 1e-9 * area
        report("bspline_knots_gprop_" + name, ok, "area %.6f (want %.6f), vol %.6f (want %.6f)"
               % (solid.Area, area, abs(solid.Volume), vol))

    for a, b, periodic in ((10, 5, False), (10, 2, False), (10, 1, False), (10, 2, True)):
        base = Part.Face(Part.Wire(bspline_ellipse(a, b, periodic=periodic).toShape()))
        check("prism_%gx%g%s" % (a, b, "_periodic" if periodic else ""), base.extrude(V(0, 0, 8)),
              8 * math.pi * a * b, 2 * math.pi * a * b + 8 * ellipse_length(a, b))
    # a plate with the ellipse cut through it: the B-spline edge reversed on its faces
    rect = Part.makePolygon([V(-15, -10, 0), V(15, -10, 0), V(15, 10, 0), V(-15, 10, 0),
                             V(-15, -10, 0)])
    plate = Part.makeFace([rect, Part.Wire(bspline_ellipse(10, 5).toShape())],
                          "Part::FaceMakerBullseye").extrude(V(0, 0, 8))
    cap = 600 - 50 * math.pi
    check("plate_hole_10x5", plate, 8 * cap, 2 * cap + 8 * (100 + ellipse_length(10, 5)))
    # an oblate spheroid 10 x 2: half the B-spline revolved, its knots
    # GeomConvert's, the middle one on the seam's middle sample
    a, c = 10, 2
    arc = bspline_ellipse(c, a, quarters=2, plane="xz",
                          knots=[1.5 * math.pi, 2 * math.pi, 2.5 * math.pi]).toShape()
    p1, p2 = arc.Vertexes[0].Point, arc.Vertexes[-1].Point
    face = Part.Face(Part.Wire([arc, Part.makeLine(p2, p1)]))
    solid = Part.Solid(Part.Shell(face.revolve(V(0, 0, 0), V(0, 0, 1), 360).Faces))
    e = math.sqrt(1 - c * c / (a * a))
    check("spheroid_%gx%g" % (a, c), solid, 4 / 3 * math.pi * a * a * c,
          2 * math.pi * a * a + math.pi * c * c / e * math.log((1 + e) / (1 - e)))


guarded(bspline_knots_gprop)


# #280: the Pocket's cut. The tool's cylinder has its rim in the plane the
# part is mirrored about; the section of the cylinder with a revolved end of
# the part runs into the corner where the rim leaves the part, tangent there
# to the arc that end meets the plane in, and stopped 0.0051 short of it. No
# solid was split: the cut was the part unchanged, the common and the fuse
# empty, with no error. The volumes wanted are those of the tool moved 0.001
# up and down, halved (README.md, "#280: a section that stops short of the
# corner it runs into").
def issue280():
    part = Part.read(os.path.join(HERE, "models", "issue280_part.brep"))
    tool = Part.read(os.path.join(HERE, "models", "issue280_tool.brep"))
    for name, want in (("cut", 70554.63), ("common", 28084.41), ("fuse", 156253.74)):
        res = getattr(part, name)(tool)
        solids = len(res.Solids)
        vol = res.Volume if solids else 0.0
        ok = res.isValid() and solids == 1 and abs(vol - want) <= 1e-5 * want
        report("issue280_pocket_%s" % name, ok,
               "%s, %d solid(s), volume %.4f (want %.2f)"
               % ("valid" if res.isValid() else "invalid", solids, vol, want))


guarded(issue280)

# #617's Pad on a torus (the model's _simple variant): the torus and the pad's
# prism, which stands on it along its own profile -- the torus' cut by
# x = 0 as the sketch keeps it, 6.1e-5 off the torus and saying so (7.3e-5):
# the profile's edge and the vertices alone ("edge"), or the wall as well, as
# FreeCAD makes the pad ("wall"). The wall is tangent to the torus at two
# points of that edge, where the second branch of their section leaves it,
# and the walking lines lose their way there. "edge" came back unfused: two
# solids, the common nothing, the cut the torus, with no error; "wall" one
# solid with a vertex of 0.041, an edge going nowhere and the fuse 3.4 short.
# The volumes wanted are those of the prism moved 0.01 along x either way,
# halved; no vertex may be looser than the profile says, and no edge has a
# face missing (README.md, "#617: a pad standing on a torus along its own
# cut").
def issue617_torus_pad():
    torus = Part.read(os.path.join(HERE, "models", "issue617_torus.brep"))
    for kind, model in (("edge", "issue617_torus_pad_edge.brep"),
                        ("wall", "issue617_torus_pad.brep")):
        pad = Part.read(os.path.join(HERE, "models", model))
        issue617_torus_pad_runs(torus, pad, kind)


def issue617_torus_pad_runs(torus, pad, kind):
    for name, want in (("cut", 70020.56), ("common", 7959.79), ("fuse", 122396.04)):
        res = getattr(torus, name)(pad)
        solids = len(res.Solids)
        vol = res.Volume if solids else 0.0
        tol = max(v.Tolerance for v in res.Vertexes) if solids else 0.0
        loose = 0
        for e in res.Edges:
            faces = res.ancestorsOfType(e, Part.Face)
            # a seam is on its one face twice; in the cut the profile is on
            # four, where the hole reaches the torus' skin along it
            if (not e.Degenerated and len(faces) % 2
                    and not (len(faces) == 1 and e.isSeam(faces[0]))):
                loose += 1
        ok = (res.isValid() and solids == 1 and abs(vol - want) <= 1e-5 * want
              and tol <= 1e-4 and loose == 0)
        report("issue617_torus_pad_%s_%s" % (kind, name), ok,
               "%s, %d solid(s), volume %.4f (want %.2f), largest vertex tolerance %.2g "
               "(want <= 1e-4), %d edge(s) with a face missing"
               % ("valid" if res.isValid() else "invalid", solids, vol, want, tol, loose))


guarded(issue617_torus_pad)


# #617's Pad itself: the revolution fused with the two prisms padded from its
# cut by z = 0 (README.md, "#617: a pad's wall standing on a revolution along
# its bottom edge"). The right volume is 127114 (the prisms 0.01 above or
# below the cut give 127121 and 127107). The tangent points are no longer
# reached by growing their vertices to the walking lines (0.0023): a curve is
# made from each line to its point.
def issue617_pad_fuse():
    rev = Part.read(os.path.join(HERE, "models", "issue617_revolution.brep"))
    prisms = Part.read(os.path.join(HERE, "models", "issue617_prisms.brep"))
    res = rev.fuse(prisms)
    solids = len(res.Solids)
    vol = res.Volume if solids else 0.0
    tol = max(v.Tolerance for v in res.Vertexes) if solids else 0.0
    ok = res.isValid() and solids == 1 and abs(vol - 127114) <= 20 and tol <= 1e-4
    report("issue617_pad_fuse", ok,
           "%s, %d solid(s), volume %.4f (want 127114 +- 20), largest vertex tolerance %.2g "
           "(want <= 1e-4)" % ("valid" if res.isValid() else "invalid", solids, vol, tol))


guarded(issue617_pad_fuse)

# #474's Helix002, a helical thread: points outside it that
# BRepClass3d_SolidClassifier said inside (a line crossing a B-spline flank
# just inside its rim was lost by IntCurvesFace_Intersector, whose polyhedron
# of the flank measured how far its border chords are from the rim on even
# steps it does not have), and the common of a line through the solid with it,
# which kept the part outside (README.md, "#474: a point outside a helix said
# inside it").
def issue474_helix_classify():
    helix = Part.read(os.path.join(HERE, "models", "issue474_helix.brep"))
    points = [(10.875, -12.661, 17.151), (12.7236, -7.6476, 12.1118), (12.5155, -12.1097, 29.2421),
              (13.2945, -8.6270, 28.0298), (12.7915, -7.0546, 25.2969), (12.5694, 7.2925, 24.5869),
              (13.1348, -10.5992, 29.5003)]
    said = [q for q in points if helix.isInside(V(*q), 1e-7, True)]
    report("issue474_helix_points", not said,
           "%d of %d points outside the solid said inside (want 0)" % (len(said), len(points)))
    p, d = V(10.875, -12.661, 17.151), V(-0.047987, 0.971357, -0.232727)
    com = helix.common(Part.makeLine(p - d * 0.001, p + d * 60))
    report("issue474_helix_line_common", len(com.Edges) == 1 and abs(com.Length - 6.7904) <= 1e-3,
           "%d edge(s), length %.4f (want 1, 6.7904)" % (len(com.Edges), com.Length))


guarded(issue474_helix_classify)

failed = results.count(False)
emit("---")
emit("summary: PASS=%d%s" % (results.count(True), "  FAIL=%d" % failed if failed else ""))
sys.stdout.flush()
os._exit(1 if failed else 0)
