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

json.dump(dict(size=[420, 420], panels=jobs), open(os.path.join(W, "jobs.json"), "w"))
json.dump(pictures, open(os.path.join(W, "pictures.json"), "w"))
emit("DONE")
os._exit(0)
