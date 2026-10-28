# FreeCADCmd prep.py -- the panels of the pictures (make_pictures.sh): the
# drivers' results (models/*.cpp --write) in $W/<fix>/before and after, laid
# out as panels; $W/jobs.json for ../../fillet/pictures/render.py and
# $W/pictures.json for compose.py.
import json
import os

import FreeCAD as App
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

json.dump(dict(size=[420, 420], panels=jobs), open(os.path.join(W, "jobs.json"), "w"))
json.dump(pictures, open(os.path.join(W, "pictures.json"), "w"))
emit("DONE")
os._exit(0)
