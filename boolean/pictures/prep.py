# FreeCADCmd prep.py -- the panels of the pictures (make_pictures.sh): the
# drivers' results (models/*.cpp --write) in $W/<fix>/before and after, laid
# out as panels; $W/jobs.json for ../../fillet/pictures/render.py and
# $W/pictures.json for compose.py.
import json
import math
import os

import FreeCAD as App
import numpy
import Part

V = App.Vector
W = os.environ["W"]
MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
ORANGE = (0.95, 0.6, 0.25)


def emit(s):
    os.write(1, (s + "\n").encode())


jobs, pictures = [], []


def panel(pic, shape, title, note, eye, center, height, colors=None, mark=False, bad=False):
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    shape.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    jobs.append(dict(brep=out, png=png, eye=eye, center=center, height=height,
                     facecolors=colors or {}, mark=mark))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
    emit("PANEL %d %s / %s" % (i, pic["name"], title))


# #64: a cylinder split by a plane tilted off its axis, with a fuzzy value;
# each solid moved off the cut along the plane's normal, the second orange.
K, SEAM, GAP = 0.35, 90, 4.0
pic = dict(name="issue064_fuzzy_plane_cylinder",
           title="#64: a cylinder split by a plane tilted off its axis (k %g), with a fuzzy value"
                 % K,
           caption="General fuse (BOPAlgo_Builder), the cylinder's seam away from the cut; "
                   "the pieces moved apart along the plane's normal, the second in orange.",
           panels=[])
n = V(0, 1, -K)
n.normalize()
for name, title, note in [
        ("after/k%g_seam%g_fuzzy0.brep", "no fuzzy value", "two pieces"),
        ("before/k%g_seam%g_fuzzy0.5.brep", "fuzzy 0.5, before",
         "one solid: the top split, the side not -- the plane was taken for parallel to the axis"),
        ("after/k%g_seam%g_fuzzy0.5.brep", "fuzzy 0.5, after",
         "two pieces, as with no fuzzy value")]:
    s = Part.Shape()
    s.read(os.path.join(W, "064", name % (K, SEAM)))
    solids = []
    for so in s.Solids:
        side = 1 if (so.CenterOfMass - V(0, 0, 34.36)).dot(n) > 0 else -1
        so = so.copy()
        so.translate(n * (GAP * side / 2 if len(s.Solids) > 1 else 0))
        solids.append(so)
    colors = {}
    if len(solids) > 1:
        first = len(solids[0].Faces)
        colors = {str(first + j): ORANGE for j in range(len(solids[1].Faces))}
    panel(pic, Part.makeCompound(solids), title, note, [1.0, -1.5, 0.7], [0, 0, 17.5], 78, colors,
          bad=len(s.Solids) < 2)
pictures.append(pic)

# #580: Pad003 mirrored and fused with its mirror; the face holding the
# degenerated edge orange, faces failing isValid() red (render.py's mark).
pic = dict(name="issue580_mirror_degenerated",
           title="#580: a solid whose planar face holds a degenerated edge, mirrored",
           caption="#580's Pad003 (700.9305), mirrored about the XZ plane with a copy "
                   "(BRepBuilderAPI_Transform), and fused with its mirror. The face holding the "
                   "degenerated edge in orange; a face failing its check in red.",
           panels=[])
pad = Part.read(os.path.join(MODELS, "issue580_pad003.brep"))
EYE = [0.5, -1.0, 1.3]
for shape, title, note, center, bad in [
        (pad, "the input", "valid, 700.9305", [-23.6, -7.1, 3.75], False),
        (Part.read(os.path.join(W, "580", "before", "mirror.brep")), "mirrored, before",
         "invalid: the degenerated edge lost its only curve; 652.3448", [-23.6, 7.1, 3.75], True),
        (Part.read(os.path.join(W, "580", "after", "mirror.brep")), "mirrored, after",
         "valid, 700.9305", [-23.6, 7.1, 3.75], False),
        (Part.read(os.path.join(W, "580", "after", "fuse.brep")), "fused with its mirror, after",
         "valid, 1209.5704: twice 700.9305 less the common", [-23.6, 0, 3.75], False)]:
    height = 62 if "fused" not in title else 84
    colors = {}
    for i, f in enumerate(shape.Faces):
        if any(e.Degenerated for e in f.Edges) and f.Surface.__class__.__name__ == "Plane":
            colors[str(i)] = ORANGE
    panel(pic, shape, title, note, EYE, center, height, colors, mark=True, bad=bad)
pictures.append(pic)

# #613: a cylinder's face, its seam 1e-8 off where the circle the plane
# z = 0 cuts from it starts; the face see-through, the section red.
pic = dict(name="issue613_seam_section",
           title="#613: a cylinder whose seam is 1e-8 off u = 0, cut by a plane",
           caption="BRepAlgoAPI_Section of a cylinder's face (r 21.2, a whole turn, its seam at "
                   "u = 1e-8) with the plane z = 0. The face is drawn see-through, the section in "
                   "red; the seam is the vertical edge in front.",
           panels=[])
for stage, title, note, bad in (
        ("before", "before", "no section: the seam's vertex stood for the circle's ends, at "
                             "1e-8, and the circle was never closed", True),
        ("after", "after", "the whole circle, 133.2035", False)):
    both = Part.read(os.path.join(W, "613", stage, "cylinder_1e-08.brep"))
    face, section = both.childShapes()[0], both.childShapes()[1]
    sec = os.path.join(W, "613_%s_section.brep" % stage)
    section.exportBrep(sec)
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    face.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    jobs.append(dict(brep=out, png=png, eye=[1.0, -0.4, 0.45], center=[0, 0, 2], height=56,
                     transparency=70,
                     extras=[dict(brep=sec, color=[0.85, 0.1, 0.1], linewidth=5)]))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
pictures.append(pic)

# A section's tangent end at a corner: the dome's fillet shape, the bottom
# removed; one mitre pair's offsets at their corner, the faces see-through,
# the section red; the thickness cut open.
MAGENTA = (0.85, 0.2, 0.85)
pic = dict(name="dome_tangent_corner",
           title="A box under a B-spline dome, its edges filleted, 2 inward with the bottom removed",
           caption="BRepOffsetAPI_MakeThickSolid::MakeThickSolidByJoin, -2, the Arc join. At each "
                   "corner of the dome two fillets meet in a mitre and both meet the dome "
                   "tangentially; the middle panels are the offsets of two of them (faces 7 and 10) "
                   "at that corner, see-through, with their section (BRepAlgoAPI_Section) in red.",
           panels=[])
dome = Part.read(os.path.join(MODELS, "dome_fillet_r3.brep"))
panel(pic, dome, "the input", "the bottom (magenta) removed, 2 inward", [-0.7, -1.0, -0.6],
      [40, 25, 18], 110, {"3": MAGENTA})
for stage, title, note, bad in (
        ("before", "before", "no section: it ended a hair outside one face and took no vertex "
                             "there; the thickness refused", True),
        ("after", "after", "the section, 1.7038 long, ends at the corner's vertex", False)):
    both = Part.read(os.path.join(W, "dome", stage, "pair7x10.brep"))
    kids = both.childShapes()
    faces = Part.Compound(kids[:2])
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    faces.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    extras = []
    if kids[2].Edges:
        sec = os.path.join(W, "dome_%s_section.brep" % stage)
        kids[2].exportBrep(sec)
        extras.append(dict(brep=sec, color=[0.85, 0.1, 0.1], linewidth=5))
    jobs.append(dict(brep=out, png=png, eye=[-0.5, -1.0, 0.9], center=[2.6, 2.6, 22.4], height=5,
                     transparency=60, extras=extras))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
thick = Part.read(os.path.join(W, "dome", "after", "thickness.brep"))
half = thick.common(Part.makeBox(100, 30, 60, V(-10, -5, -5)))
panel(pic, half, "after, cut open", "valid, 20254.4308, the volume booleans give; beyond y = 25 cut "
      "away", [0.5, 1.2, 0.6], [40, 12, 15], 100, mark=True)
pictures.append(pic)

# #617: the revolution cut by z = 0, the cut red; the two prisms on its
# lobes with the lines of their side faces' spans (the cut's knots) red --
# the whole and the knots bunched where the cut turns; the integrals'
# numbers, before and after, from the driver's output.
def prisms_line(stage):
    for line in open(os.path.join(W, "617", stage + ".txt")):
        if line.startswith("prisms:"):
            w = line.split()
            return float(w[2]), float(w[4].rstrip(",")), float(w[8]), float(w[10].rstrip(","))


pic = dict(name="issue617_gprop",
           title="#617: two prisms on the cut of a revolution, their volume and area",
           caption="BRepGProp::VolumeProperties and SurfaceProperties (no precision given, what "
                   "Shape.Volume and Shape.Area run). The cut (BRepAlgoAPI_Section, Approximation "
                   "on) is two degree 8 B-splines of 29 spans; the red lines on the prisms are its "
                   "knots. Held against the shoelace over a dense polygon of each lobe and the "
                   "curve's length.",
           panels=[])
rev = Part.read(os.path.join(W, "617", "after", "revolution.brep"))
sec = os.path.join(W, "617_section.brep")
Part.read(os.path.join(W, "617", "after", "section.brep")).exportBrep(sec)
bb = rev.BoundBox
i = len(jobs)
out = os.path.join(W, "panel%d.brep" % i)
rev.exportBrep(out)
png = os.path.join(W, "panel%d.png" % i)
jobs.append(dict(brep=out, png=png, eye=[0.6, -1.0, 0.8], center=[bb.Center.x, bb.Center.y,
                 bb.Center.z], height=1.1 * max(bb.XLength, bb.YLength, bb.ZLength),
                 transparency=70, extras=[dict(brep=sec, color=[0.85, 0.1, 0.1], linewidth=5)]))
pic["panels"].append(dict(png=png, title="the input", note="the revolution, cut by z = 0 (red): "
                          "two lobes", bad=False))
prisms = Part.read(os.path.join(W, "617", "after", "prisms.brep"))
ticks = []
for e in Part.read(os.path.join(W, "617", "after", "section.brep")).Edges:
    for k in e.Curve.getKnots():
        p = e.Curve.value(k)
        ticks.append(Part.makeLine(V(p.x, p.y, 0), V(p.x, p.y, 100)))
knots = os.path.join(W, "617_knots.brep")
Part.makeCompound(ticks).exportBrep(knots)
bv, vw, ba, aw = prisms_line("before")
av, _, aa, _ = prisms_line("after")
pb = prisms.BoundBox
# where the knots bunch: the densest stretch of nine knots along the cut
pts = sorted((t.Vertexes[1].Point for t in ticks), key=lambda q: q.x)
best = min(range(len(pts) - 8), key=lambda j: (pts[j + 8] - pts[j]).Length)
zoom = (pts[best] + pts[best + 8]) * 0.5
span = max((pts[best + 8] - pts[best]).Length, 2.0)
EYE617 = [0.3, -0.55, 1.0]
for title, note, center, height, bad in (
        ("before", "volume %.1f (%+.0f%%), area %.1f (%+.0f%%) for %.2f and %.2f"
         % (bv, 100 * (bv / vw - 1), ba, 100 * (ba / aw - 1), vw, aw),
         [pb.Center.x, pb.Center.y, pb.Center.z], 1.2 * max(pb.XLength, pb.YLength) + 40, True),
        ("after: the knots bunched, near", "volume %.4f, area %.4f: the shoelace's to 1e-7"
         % (av, aa), [zoom.x, zoom.y, 100], 4 * span, False)):
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    prisms.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    jobs.append(dict(brep=out, png=png, eye=EYE617, center=center, height=height,
                     extras=[dict(brep=knots, color=[0.85, 0.1, 0.1], linewidth=2)]))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
pictures.append(pic)

# An offset surface integrated at 18 points: the prism on an ellipse of 10 x 2
# offset by 1, the wall (the offset surface) orange; before, the 18 points
# the rule over the turn took (iso lines, red), after, where the turn is cut
# in pieces of 20 points each -- graded toward where the basis's normal
# turns fastest, as the integral finds it on three iso lines.
def offset_line(stage, case):
    for line in open(os.path.join(W, "off", stage + ".txt")):
        if line.startswith(case):
            w = line.replace(",", " ").replace("(", " ").split()
            return float(w[w.index("volume") + 1]), float(w[w.index("area") + 1]), \
                float(w[w.index("volume") + 3]), float(w[w.index("area") + 3])


def iso_lines(face, us):
    u0, u1, v0, v1 = face.ParameterRange
    return Part.makeCompound([Part.Edge(face.Surface.uIso(u), v0, v1) for u in us])


def turning_pieces(face, basis=None):
    # BRepGProp_Gauss.cxx, turningBreaks: the seam and the breaks in u, on the
    # surface whose normal is sampled (an offset's basis)
    u0, u1, v0, v1 = face.ParameterRange
    basis = basis or face.Surface.BasisSurface
    rates = [0.0] * 128
    for w in (1, 2, 3):
        v = v0 + (v1 - v0) * w / 4.0
        ns = [basis.normal(u0 + (u1 - u0) * i / 128.0, v) for i in range(129)]
        for i in range(128):
            rates[i] = max(rates[i], ns[i].getAngle(ns[i + 1]) * 128 / (u1 - u0))
    top = max(rates)
    sums = [0.0]
    for r in rates:
        sums.append(sums[-1] + math.sqrt(r * top) * (u1 - u0) / 128)
    k = min(64, int(math.ceil(sums[-1])))
    cuts, i = [u0], 0
    for j in range(1, k):
        s = sums[-1] * j / k
        while sums[i + 1] < s:
            i += 1
        cuts.append(u0 + (u1 - u0) * (i + (s - sums[i]) / (sums[i + 1] - sums[i])) / 128)
    return cuts, k


pic = dict(name="offset_surface_gprop",
           title="An offset surface: a prism on an ellipse of 10 x 2 (height 8), offset by 1",
           caption="BRepOffsetAPI_MakeOffsetShape, the Intersection join: the wall (orange) the "
                   "offset of the prism's, the caps planes. Its volume and area by BRepGProp "
                   "(no precision given), held against Steiner's: the offset region's area "
                   "pi a b + L d + pi d^2 times the height 10.",
           panels=[])
solid = Part.read(os.path.join(W, "off", "after", "10x2_1.brep"))
wall = [i for i, f in enumerate(solid.Faces) if f.Surface.__class__.__name__ == "OffsetSurface"]
wf = solid.Faces[wall[0]]
u0, u1 = wf.ParameterRange[:2]
nodes = numpy.polynomial.legendre.leggauss(18)[0]
before_lines = iso_lines(wf, [0.5 * (u0 + u1) + 0.5 * (u1 - u0) * x for x in nodes])
cuts, k = turning_pieces(wf)
after_lines = iso_lines(wf, cuts)
bv, ba, vw, aw = offset_line("before", "10x2 d +1")
av, aa, _, _ = offset_line("after", "10x2 d +1")
bb = solid.BoundBox
for title, note, lines, bad in (
        ("before: one rule of 18 points", "volume %.3f (%+.1f%%), area %.3f (%+.2f%%) for %.3f "
         "and %.3f" % (bv, 100 * (bv / vw - 1), ba, 100 * (ba / aw - 1), vw, aw), before_lines,
         True),
        ("after: %d pieces of 20 points" % k, "volume %.6f, area %.6f: Steiner's to 1e-9"
         % (av, aa), after_lines, False)):
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    solid.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    ln = os.path.join(W, "off_lines%d.brep" % i)
    lines.exportBrep(ln)
    jobs.append(dict(brep=out, png=png, eye=[0.35, -0.8, 1.0], center=[0, 0, 4],
                     height=1.15 * max(bb.XLength, bb.YLength), facecolors={str(wall[0]): ORANGE},
                     extras=[dict(brep=ln, color=[0.85, 0.1, 0.1], linewidth=2)]))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
pictures.append(pic)

# An ellipse's extrusion: its area integrated at 18 points -- the prism on an
# ellipse of 10 x 2, its wall (an extrusion) orange; before, the 18 points the
# rule over the turn took (iso lines, red), after, the pieces of 20 points
# each, graded toward where the wall's normal turns fastest.
def ext_line(stage, case, fix="ext", what="area"):
    for line in open(os.path.join(W, fix, stage + ".txt")):
        if line.startswith(case + ":"):
            w = line.replace(",", " ").replace("(", " ").split()
            return float(w[w.index(what) + 1]), float(w[w.index(what) + 3])


pic = dict(name="extrusion_area_gprop",
           title="An ellipse's extrusion: a prism on an ellipse of 10 x 2 (height 8)",
           caption="BRepPrimAPI_MakePrism: the wall (orange) the extrusion of the ellipse, the "
                   "caps planes. Its area by BRepGProp (no precision given), held against "
                   "2 pi a b + 8 L, L the ellipse's length. The volume was exact before and is.",
           panels=[])
solid = Part.read(os.path.join(W, "ext", "after", "prism_10x2.brep"))
wall = [i for i, f in enumerate(solid.Faces)
        if f.Surface.__class__.__name__ == "SurfaceOfExtrusion"]
wf = solid.Faces[wall[0]]
u0, u1 = wf.ParameterRange[:2]
nodes = numpy.polynomial.legendre.leggauss(18)[0]
before_lines = iso_lines(wf, [0.5 * (u0 + u1) + 0.5 * (u1 - u0) * x for x in nodes])
cuts, k = turning_pieces(wf, wf.Surface)
after_lines = iso_lines(wf, cuts)
ba, aw = ext_line("before", "prism_10x2")
aa, _ = ext_line("after", "prism_10x2")
bb = solid.BoundBox
for title, note, lines, bad in (
        ("before: one rule of 18 points", "area %.4f (%+.2f%%) for %.4f"
         % (ba, 100 * (ba / aw - 1), aw), before_lines, True),
        ("after: %d pieces of 20 points" % k, "area %.6f: the closed form's to 1e-15" % aa,
         after_lines, False)):
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    solid.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    ln = os.path.join(W, "ext_lines%d.brep" % i)
    lines.exportBrep(ln)
    jobs.append(dict(brep=out, png=png, eye=[0.35, -0.8, 1.0], center=[0, 0, 4],
                     height=1.15 * max(bb.XLength, bb.YLength), facecolors={str(wall[0]): ORANGE},
                     extras=[dict(brep=ln, color=[0.85, 0.1, 0.1], linewidth=2)]))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
pictures.append(pic)

# A B-spline integrated across its knots -- the prism on an ellipse of 10 x 2
# made GeomConvert's rational B-spline (three spans, C1 at its knots), the
# caps orange; before, the 18 points the rule along the caps' edge took over
# all three spans (iso lines of the wall, the edge's parameter, red); after,
# the edge cut at its knots, each span its own rule.
pic = dict(name="bspline_knots_gprop",
           title="A B-spline integrated across its knots: a prism on an ellipse of 10 x 2",
           caption="Height 8. GeomConvert::CurveToBSplineCurve: the ellipse a periodic "
                   "rational B-spline of degree 2, three spans, its derivatives jumping at "
                   "the knots; the caps "
                   "(orange) bounded by it. The area and volume by BRepGProp (no precision "
                   "given), held against 2 pi a b + 8 L and 8 pi a b.",
           panels=[])
solid = Part.read(os.path.join(W, "knots", "after", "prism_10x2.brep"))
wall = [i for i, f in enumerate(solid.Faces)
        if f.Surface.__class__.__name__ == "SurfaceOfExtrusion"]
caps = [i for i, f in enumerate(solid.Faces) if f.Surface.__class__.__name__ == "Plane"]
wf = solid.Faces[wall[0]]
u0, u1 = wf.ParameterRange[:2]
nodes = numpy.polynomial.legendre.leggauss(18)[0]
before_lines = iso_lines(wf, [0.5 * (u0 + u1) + 0.5 * (u1 - u0) * x for x in nodes])
knots = [k for k in wf.Surface.BasisCurve.getKnots() if u0 < k < u1]
after_lines = iso_lines(wf, [u0] + knots)
ba, aw = ext_line("before", "prism_10x2", "knots")
aa, _ = ext_line("after", "prism_10x2", "knots")
bv, vw = ext_line("before", "prism_10x2", "knots", "volume")
av, _ = ext_line("after", "prism_10x2", "knots", "volume")
bb = solid.BoundBox
for title, note, lines, bad in (
        ("before: 18 points over 3 spans",
         "area %.4f (%+.2f%%) for %.4f, volume %.4f (%+.2f%%)"
         % (ba, 100 * (ba / aw - 1), aw, bv, 100 * (bv / vw - 1)), before_lines, True),
        ("after: %d pieces, cut at the knots" % (len(knots) + 1),
         "area %.6f, volume %.6f: the closed forms' to 1e-15" % (aa, av),
         after_lines, False)):
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    solid.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    ln = os.path.join(W, "knots_lines%d.brep" % i)
    lines.exportBrep(ln)
    jobs.append(dict(brep=out, png=png, eye=[0.35, -0.8, 1.0], center=[0, 0, 4],
                     height=1.15 * max(bb.XLength, bb.YLength),
                     facecolors={str(c): ORANGE for c in caps},
                     extras=[dict(brep=ln, color=[0.85, 0.1, 0.1], linewidth=2)]))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
pictures.append(pic)

# The adaptive integral refined along the edges only -- #617's prisms, their
# walls (extrusions of degree 8 B-splines of 29 spans) orange; before, where
# the rule across u started and stayed, one interval over the whole curve
# (iso lines at its ends, red); after, the intervals it starts from, the
# curve's knots, refined from there.
def adapt_line(stage):
    for line in open(os.path.join(W, "adapt", stage + ".txt")):
        if line.startswith("issue617_prisms:"):
            w = line.replace(",", " ").replace("(", " ").replace(")", " ").split()
            g = [j for j, t in enumerate(w) if t == "given"]
            return dict(area=float(w[w.index("area") + 1]), area_ref=float(w[w.index("area") + 3]),
                        vol=float(w[w.index("volume") + 1]),
                        vol_ref=float(w[w.index("volume") + 3]),
                        area_err=float(w[g[0] + 1]), vol_err=float(w[g[1] + 1]))


pic = dict(name="adaptive_gprop",
           title="The adaptive integral refined along the edges only: #617's prisms",
           caption="BRepGProp::VolumeProperties and SurfaceProperties given a precision of 1e-6 "
                   "(the adaptive integrals; Shape.Volume and Shape.Area run the plain ones). The "
                   "walls (orange) are extrusions of degree 8 B-splines of 29 spans. Held against "
                   "the shoelace over a dense polygon of each cap and the curve's length.",
           panels=[])
prisms = Part.read(os.path.join(W, "adapt", "after", "issue617_prisms.brep"))
walls = [i for i, f in enumerate(prisms.Faces)
         if f.Surface.__class__.__name__ == "SurfaceOfExtrusion"]
before_lines, after_lines = [], []
for i in walls:
    f = prisms.Faces[i]
    u0, u1 = f.ParameterRange[:2]
    before_lines.append(iso_lines(f, [u0, u1]))
    after_lines.append(iso_lines(f, [u0] + [k for k in f.Surface.BasisCurve.getKnots()
                                            if u0 < k < u1]))
b, a = adapt_line("before"), adapt_line("after")
pb = prisms.BoundBox
for title, note, lines, bad in (
        ("before: one interval, never refined",
         "volume %.1f (%+.0f%%), area %.1f (%+.0f%%) for %.2f and %.2f; the error given %.1g"
         % (b["vol"], 100 * (b["vol"] / b["vol_ref"] - 1), b["area"],
            100 * (b["area"] / b["area_ref"] - 1), b["vol_ref"], b["area_ref"],
            max(b["vol_err"], b["area_err"])), Part.makeCompound(before_lines), True),
        ("after: from the knots, refined",
         "volume %.4f, area %.4f: the shoelace's to %.0e"
         % (a["vol"], a["area"], max(abs(a["vol"] / a["vol_ref"] - 1),
                                     abs(a["area"] / a["area_ref"] - 1))),
         Part.makeCompound(after_lines), False)):
    i = len(jobs)
    out = os.path.join(W, "panel%d.brep" % i)
    prisms.exportBrep(out)
    png = os.path.join(W, "panel%d.png" % i)
    ln = os.path.join(W, "adapt_lines%d.brep" % i)
    lines.exportBrep(ln)
    jobs.append(dict(brep=out, png=png, eye=EYE617, center=[pb.Center.x, pb.Center.y,
                     pb.Center.z], height=1.2 * max(pb.XLength, pb.YLength) + 40,
                     facecolors={str(c): ORANGE for c in walls},
                     extras=[dict(brep=ln, color=[0.85, 0.1, 0.1], linewidth=2)]))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))
pictures.append(pic)

json.dump(dict(size=[420, 420], panels=jobs), open(os.path.join(W, "jobs.json"), "w"))
json.dump(pictures, open(os.path.join(W, "pictures.json"), "w"))
emit("DONE")
os._exit(0)
