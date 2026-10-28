# python3 prep.py -- the panels of the pictures (make_pictures.sh): the
# shapes the drivers read back from STEP (models/*.cpp <dir>) in
# $W/<fix>/before and after, with the colours read back on their faces;
# $W/jobs.json for ../../fillet/pictures/render.py and $W/pictures.json for
# ../../boolean/pictures/compose.py.
import json
import os

W = os.environ["W"]
jobs, pictures = [], []


def colours(path):
    out = {}
    if os.path.exists(path):
        for line in open(path):
            i, r, g, b = line.split()
            out[i] = [float(r), float(g), float(b)]
    return out


def panel(pic, brep, cols, title, note, eye, bad=False):
    i = len(jobs)
    png = os.path.join(W, "panel%d.png" % i)
    jobs.append(dict(brep=brep, png=png, eye=eye, center=[0, 0, 5], height=24, facecolors=cols))
    pic["panels"].append(dict(png=png, title=title, note=note, bad=bad))


# #310: FreeCAD's Part::Cylinder (a prism of its bottom face, the top that
# face moved up), top red and bottom blue, written to STEP and read back
pic = dict(name="issue310_step_partner_colours",
           title="#310: a cylinder's end colours written to STEP and read back",
           caption="A prism of the cylinder's bottom face, as FreeCAD's Part::Cylinder: its top "
                   "is the bottom face moved up, one TShape at two places. Coloured top red, "
                   "bottom blue, written with the STEP writer's defaults and read back. A face "
                   "read back with no colour is drawn in the viewer's grey-blue.",
           panels=[])
for stage, title, note in (
        ("before", "before", "the top's red on the bottom, the top without colour"),
        ("after", "after", "top red, bottom blue, as given")):
    brep = os.path.join(W, "310", stage, "prism.brep")
    cols = colours(os.path.join(W, "310", stage, "prism.colours"))
    panel(pic, brep, cols, title + ", from above", note, [0.6, -1.0, 0.9], bad=stage == "before")
    panel(pic, brep, cols, title + ", from below", note, [0.6, -1.0, -0.9], bad=stage == "before")
pictures.append(pic)

json.dump(dict(size=[340, 340], panels=jobs), open(os.path.join(W, "jobs.json"), "w"))
json.dump(pictures, open(os.path.join(W, "pictures.json"), "w"))
print("DONE")
