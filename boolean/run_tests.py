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
import time
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


# The same pad on a torus cut through a plane of symmetry (R 30, r 12 about
# y, the plane x = 10; both curves of the cut, each its own mirror image in
# y = 0): towards +x ("forward"), towards -x ("back"), and towards +x with
# each curve cut in two near y = 0 ("split"), as FreeCAD's face maker had
# them until 2026-11-13. Several walking lines of one wall go by one tangent
# point: forward gave one solid with a vertex of 0.028 and the fuse 11.4
# short, split an invalid fuse with a vertex of 11 and half the common, and
# back was right at more than 100 s a boolean. The volumes wanted are those
# of the prism moved 0.01 along x either way, halved; the solids are counted
# (what is left of the torus beyond the plane touches the rest along the
# profile only), no vertex may be looser than the profile says (a section
# curve of "split" is given as 2.2e-4), no edge has a face missing, and none
# takes a minute (README.md, "#617: the same line more than once past a
# tangent point").
#
# And the pad on a torus about a tilted axis, on both curves of its cut by
# x = 0 (mirror images of each other only): towards +x ("tilt") and towards
# -x ("tiltback"), where two lines of one wall go by one tangent point, one of
# them given as 1.1e-3 and swinging 0.018 out of its wall past the point --
# valid, a vertex of 0.0135, the fuse 4.6 short.
def issue617_symtorus_pad():
    sym = Part.read(os.path.join(HERE, "models", "issue617_symtorus.brep"))
    tilted = Part.read(os.path.join(HERE, "models", "issue617_tilttorus.brep"))
    forward = (("cut", 68644.34, 2), ("common", 16629.04, 2), ("fuse", 126823.24, 1))
    back = (("cut", 50970.12, 4), ("common", 34303.27, 2), ("fuse", 109149.01, 1))
    tilt = (("cut", 46379.70, 2), ("common", 32890.45, 2), ("fuse", 108216.35, 1))
    tiltback = (("cut", 63229.37, 2), ("common", 16040.78, 2), ("fuse", 125066.03, 1))
    for torus, kind, model, runs, tolmax in (
            (sym, "forward", "issue617_symtorus_pad.brep", forward, 1e-4),
            (sym, "back", "issue617_symtorus_pad_back.brep", back, 1e-4),
            (sym, "split", "issue617_symtorus_pad_split.brep", forward, 3e-4),
            (tilted, "tilt", "issue617_tilttorus_pad.brep", tilt, 1e-4),
            (tilted, "tiltback", "issue617_tilttorus_pad_back.brep", tiltback, 1e-3)):
        pad = Part.read(os.path.join(HERE, "models", model))
        for name, want, nsolids in runs:
            start = time.time()
            res = getattr(torus, name)(pad)
            took = time.time() - start
            solids = len(res.Solids)
            vol = res.Volume if solids else 0.0
            tol = max(v.Tolerance for v in res.Vertexes) if solids else 0.0
            loose = 0
            for e in res.Edges:
                faces = res.ancestorsOfType(e, Part.Face)
                if (not e.Degenerated and len(faces) % 2
                        and not (len(faces) == 1 and e.isSeam(faces[0]))):
                    loose += 1
            ok = (res.isValid() and solids == nsolids and abs(vol - want) <= 1e-5 * want
                  and tol <= tolmax and loose == 0 and took < 60.0)
            report("issue617_symtorus_pad_%s_%s" % (kind, name), ok,
                   "%s, %d solid(s) (want %d), volume %.4f (want %.2f), largest vertex "
                   "tolerance %.2g (want <= %.0e), %d edge(s) with a face missing, %.1f s "
                   "(want < 60)"
                   % ("valid" if res.isValid() else "invalid", solids, nsolids, vol, want,
                      tol, tolmax, loose, took))


guarded(issue617_symtorus_pad)


# The prism of cut curves moved into the symmetric torus, 0.003, 0.01 and
# 0.05 along -x. Its bottom edge crosses the torus at a grazing angle near
# each tangent point; the vertex made there had its tolerance stretched to
# 0.3, the length the edge lies on the torus each way, and was put on a
# section line that only passes it, 0.046 off. Five edges in one vertex
# 0.046 wide, a face of the torus not made: the common nothing, the cut the
# torus less 31 and the fuse 38 short, valid and with no error. The volumes
# wanted are the prism of whole curves' own at the same places, which was
# right (README.md, "A vertex stretched onto a line that passes it"). The
# prism's own tolerance is 8.07e-5 and the results' vertices have 8.08e-5 on
# x86; on arm64 one section edge of the cut and the common at 0.01 ends
# 3.7e-5 from its vertex, which gets 1.24e-4 (the volumes the same). The
# fault was vertices of 0.0023, so the limit is 2e-4.
def issue617_symtorus_sunk():
    torus = Part.read(os.path.join(HERE, "models", "issue617_symtorus.brep"))
    split = Part.read(os.path.join(HERE, "models", "issue617_symtorus_pad_split.brep"))
    for depth, wants in ((0.003, (68641.43, 16631.95, 126820.33)),
                         (0.01, (68634.65, 16638.73, 126813.55)),
                         (0.05, (68595.89, 16677.49, 126774.79))):
        pad = split.copy()
        pad.translate(App.Vector(-depth, 0, 0))
        for name, want, nsolids in zip(("cut", "common", "fuse"), wants, (2, 2, 1)):
            res = getattr(torus, name)(pad)
            solids = len(res.Solids)
            vol = res.Volume if solids else 0.0
            tol = max(v.Tolerance for v in res.Vertexes) if solids else 0.0
            ok = (res.isValid() and solids == nsolids and abs(vol - want) <= 1e-5 * want
                  and tol <= 2e-4)
            report("issue617_symtorus_sunk_%g_%s" % (depth, name), ok,
                   "%s, %d solid(s) (want %d), volume %.4f (want %.2f), largest vertex "
                   "tolerance %.2g (want <= 2e-4)"
                   % ("valid" if res.isValid() else "invalid", solids, nsolids, vol, want, tol))


guarded(issue617_symtorus_sunk)


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


# #474's coil with the upright edge at its foot filleted: points said on the
# wrong side of it, and the common of a line with it, which kept the part
# outside. The coil's first helical face ends 1.7e-8 past a knot of its
# surface, and the polyhedron IntCurvesFace_Intersector made of it had a
# last row of triangles that wide for its border: a line crossing the face
# near its edge was lost (README.md, "A face that ends a hair past a knot of
# its surface").
def issue474_coil_classify():
    coil = Part.read(os.path.join(HERE, "models", "issue474_coil_edge_filleted.brep"))
    outside = [(-12.958, -0.347, 9.870), (-12.883, -0.886, 9.834)]
    inside = [(-12.896, -0.814, 11.676), (-12.885, -0.931, 11.869)]
    wrong = ([q for q in outside if coil.isInside(V(*q), 1e-7, True)]
             + [q for q in inside if not coil.isInside(V(*q), 1e-7, True)])
    report("issue474_coil_points", not wrong,
           "%d of %d points said on the wrong side of the solid (want 0)"
           % (len(wrong), len(outside) + len(inside)))
    p, d = V(-12.958, -0.347, 9.870), V(-0.001308, 0.061261, 0.998121)
    com = coil.common(Part.makeLine(p - d * 0.3, p + d * 2.0))
    report("issue474_coil_line_common", len(com.Edges) == 1 and abs(com.Length - 0.8509) <= 1e-3,
           "%d edge(s), length %.4f (want 1, 0.8509)" % (len(com.Edges), com.Length))


guarded(issue474_coil_classify)


# The prisms padded from #617's cuts, their walls extrusions of B-splines:
# points outside them said inside. The point's line passed through a bulge
# of a wall, crossing it twice close by, a few degrees off its tangent
# plane or less, and IntCurvesFace_Intersector returned the second crossing
# alone, going out. A line whose first crossing grazes the face is not
# believed alone (README.md, "A line that grazes a face").
def issue617_grazing_classify():
    for tag, name, points in (
            ("tilt", "issue617_tilttorus_pad.brep",
             [(24.190250, 31.107302, -26.782223), (10.668823, 30.842055, -25.857114),
              (-4.417922, 5.393937, -38.464740), (5.556987, 29.908879, -22.223268),
              (61.275644, 5.484870, -35.884340)]),
            ("tiltback", "issue617_tilttorus_pad_back.brep",
             [(-64.417922, 5.393937, -38.464740), (-56.791860, 30.220370, -23.466659),
              (-18.876547, 31.332908, -27.669281), (-16.536926, 31.875933, -29.833540),
              (-16.616102, 31.442742, -28.171500), (1.275644, 5.484870, -35.884340),
              (-19.710294, 29.986907, -22.564094), (-35.809750, 31.107302, -26.782223)]),
            ("sym", "issue617_symtorus_pad_split.brep", [(22.792941, 13.425282, 29.594097)])):
        pads = Part.read(os.path.join(HERE, "models", name))
        said = [q for q in points if pads.isInside(V(*q), 1e-7, True)]
        report("issue617_%s_pad_points" % tag, not said,
               "%d of %d points outside the prisms said inside (want 0)"
               % (len(said), len(points)))


guarded(issue617_grazing_classify)


# #631's Fillet001 with two edges at a vertex chamfered at 1, the corner set
# back and closed by a patch with edges of tolerance 0.011: points inside
# the solid that BRepClass3d_SolidClassifier said outside. Its line from the
# point passed such an edge within the edge's tolerance, 0.008 from its
# curve, and the pass was taken for a crossing into the solid, as of a line
# through the edge (README.md, "A line that passes an edge within its
# tolerance").
def issue631_chamfer_classify():
    solid = Part.read(os.path.join(HERE, "models", "issue631_chamfer_corner.brep"))
    points = [(46.955725, 37.499967, 94.849289), (45.004238, 36.470048, 92.334427),
              (46.088384, 37.300863, 93.738921), (47.028547, 38.460188, 95.627670),
              (45.918066, 38.248505, 94.513218), (46.490766, 38.643030, 95.362799),
              (47.462874, 37.663013, 95.246202), (46.673168, 37.377404, 94.545603),
              (46.843711, 37.733031, 94.788969), (47.461501, 37.914552, 95.870643),
              (45.799292, 37.038818, 93.248019), (45.665392, 38.194349, 94.241543),
              (46.968651, 38.873260, 95.988404)]
    said = [q for q in points if not solid.isInside(V(*q), 1e-7, True)]
    report("issue631_chamfer_points", not said,
           "%d of %d points inside the solid said outside (want 0)" % (len(said), len(points)))
    # #962 with two edges chamfered at 0.3, the corner set back, a patch with
    # edges of 0.0024: the line passes one of them 0.0008 from its curve and
    # crosses the edge's two faces a thousandth either side of the pass, in
    # and then out; the first crossing made the point outside.
    solid = Part.read(os.path.join(HERE, "models", "issue962_chamfer_corner.brep"))
    points = [(38.409, 26.466, 14.86), (38.428167, 26.430298, 14.902213)]
    said = [q for q in points if not solid.isInside(V(*q), 1e-7, True)]
    report("issue962_chamfer_points", not said,
           "%d of %d points inside the solid said outside (want 0)" % (len(said), len(points)))


guarded(issue631_chamfer_classify)


# The filleted tube's top removed 1.5 inward (thickness sec 105): the wall
# with a sealed cavity, the cavity's roof two tubes as B-splines, each a
# strip 0.58 wide of a surface 50 round. Points in the material above the
# cavity said outside: the line from the point crossed a strip 0.03 from its
# edge, and the polyhedron IntCurvesFace_Intersector looks for crossings on
# -- 20 samples either way, its facets 0.1 off the surface round, its rows
# 0.03 across -- ended at the face's bounds, so the line passed its last
# facet by. The polyhedron reaches past the bounds by its sag now
# (README.md, "A line that crosses a face nearer its border than the
# facets' sag").
def tube_cavity_classify():
    solid = Part.read(os.path.join(HERE, "models", "tube_sealed_cavity.brep"))
    points = [(5.844742553333418, -6.800981997991345, 11.879971117546765),
              (-8.787711054101528, 1.142866258707752, 11.936822531014494),
              (-8.120154, -0.688250, 11.153003), (5.685867, -6.660454, 11.609178),
              (-8.606669, 0.391817, 11.826856), (5.929184, -6.700331, 11.823056),
              (-8.332290, 0.007389, 11.397841), (-8.210914, -0.601261, 11.322987),
              (-8.789280, 1.259816, 11.916995)]
    said = [q for q in points if not solid.isInside(V(*q), 1e-7, True)]
    report("tube_cavity_points", not said,
           "%d of %d points inside the solid said outside (want 0)" % (len(said), len(points)))


guarded(tube_cavity_classify)


# The tube with its top edges filleted, its inner wall removed 1.002 inward
# (thickness sec 105): the rim round the wall's tangent edge is a tube as a
# B-spline, 20 samples round it, the facets of its polyhedron 0.09 inside
# it. A line 8 degrees off that surface, crossing it 0.37 from the tube's
# end, crosses the facets' planes beyond the last facet, where the surface
# ends and no facet can be added: the interference of a segment with the
# facets through a grid of their boxes looked for a crossing of the facet
# alone, where the one without a grid allows the facets' deflection. Five
# points in the material under the top, said outside (README.md, "A line
# that passes the last facet within the facets' deflection").
def tube_rim_classify():
    solid = Part.read(os.path.join(HERE, "models", "tube_inner_wall_in.brep"))
    points = [(-7.297521750703828, 0.6405514836882666, 11.680413377932933),
              (-7.124092, -0.079036, 11.338356), (-7.127454, -0.117618, 11.346981),
              (-7.368267, 0.906140, 11.793830), (-7.251724, 0.493717, 11.594139)]
    said = [q for q in points if not solid.isInside(V(*q), 1e-7, True)]
    report("tube_rim_points", not said,
           "%d of %d points inside the solid said outside (want 0)" % (len(said), len(points)))


guarded(tube_rim_classify)


# A solid made of a compsolid (BRepLib_MakeSolid): the faces met once, in
# the order they are met. They came out of a map keyed by the shape, in the
# order of the addresses the faces happened to have -- another from one run
# to the next (FreeCAD's Connect of a box and a cylinder, #523: an edge of
# the result Edge3 in one run and Edge6 in the next). Here the pieces of a
# box and a cylinder's general fuse, as Connect merges them (README.md, "A
# solid of a compsolid, its faces in another order every run").
def makesolid_face_order():
    box = Part.makeBox(10, 10, 10)
    cyl = Part.makeCylinder(2, 10)
    pieces = box.generalFuse([cyl])[0].Solids
    comp = Part.CompSolid(pieces)
    met, count = [], []
    for sh in comp.Shells:
        for f in sh.Faces:
            for k, g in enumerate(met):
                if g.isSame(f):
                    count[k] += 1
                    break
            else:
                met.append(f)
                count.append(1)
    want = [f for f, n in zip(met, count) if n % 2]
    solid = Part.makeSolid(comp)
    got = solid.Faces
    ok = len(got) == len(want) and all(a.isSame(b) for a, b in zip(got, want))
    report("makesolid_face_order", ok and solid.isValid(),
           "%d faces (want %d), %s the order they are met in, %s" % (
               len(got), len(want), "in" if ok else "NOT in",
               "valid" if solid.isValid() else "invalid"))


guarded(makesolid_face_order)

failed = results.count(False)
emit("---")
emit("summary: PASS=%d%s" % (results.count(True), "  FAIL=%d" % failed if failed else ""))
sys.stdout.flush()
os._exit(1 if failed else 0)
