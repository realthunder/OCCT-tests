# FreeCADCmd prep.py -- the panels of the pictures (make_pictures.sh): the
# driver's results (models/issue064_fuzzy_plane_cylinder.cpp --write) in
# $W/before and $W/after, each solid moved off the cut along the plane's
# normal so the pieces show apart, the second in orange; $W/jobs.json for
# ../../fillet/pictures/render.py and $W/panels.json for compose.py.
import json
import os

import FreeCAD as App
import Part

V = App.Vector
W = os.environ["W"]
K, SEAM, GAP = 0.35, 90, 4.0
# (file, title, lines under it)
PANELS = [
    ("after/k%g_seam%g_fuzzy0.brep", "no fuzzy value", "two pieces"),
    ("before/k%g_seam%g_fuzzy0.5.brep", "fuzzy 0.5, before",
     "one solid: the top split, the side not -- the plane was taken for parallel to the axis"),
    ("after/k%g_seam%g_fuzzy0.5.brep", "fuzzy 0.5, after", "two pieces, as with no fuzzy value"),
]


def emit(s):
    os.write(1, (s + "\n").encode())


n = V(0, 1, -K)
n.normalize()
jobs, panels = [], []
for i, (name, title, note) in enumerate(PANELS):
    s = Part.Shape()
    s.read(os.path.join(W, name % (K, SEAM)))
    solids = []
    for so in s.Solids:
        side = 1 if (so.CenterOfMass - V(0, 0, 34.36)).dot(n) > 0 else -1
        so = so.copy()
        so.translate(n * (GAP * side / 2 if len(s.Solids) > 1 else 0))
        solids.append(so)
    out = os.path.join(W, "panel%d.brep" % i)
    Part.makeCompound(solids).exportBrep(out)
    colors = {}
    if len(solids) > 1:
        first = len(solids[0].Faces)
        colors = {str(first + j): (0.95, 0.6, 0.25) for j in range(len(solids[1].Faces))}
    png = os.path.join(W, "panel%d.png" % i)
    jobs.append(dict(brep=out, png=png, eye=[1.0, -1.5, 0.7], center=[0, 0, 17.5], height=78,
                     facecolors=colors))
    panels.append(dict(png=png, title=title, note=note, solids=len(s.Solids),
                       volumes=["%.4f" % so.Volume for so in s.Solids]))
    emit("PANEL %d %s solids %d" % (i, name % (K, SEAM), len(s.Solids)))
json.dump(dict(size=[420, 420], panels=jobs), open(os.path.join(W, "jobs.json"), "w"))
json.dump(dict(k=K, panels=panels), open(os.path.join(W, "panels.json"), "w"))
emit("DONE")
os._exit(0)
