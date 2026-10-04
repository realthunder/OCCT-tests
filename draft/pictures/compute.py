# FreeCADCmd compute.py -- draft one case and keep what came out.
#
# env: DRAFT_TOOLS = this directory, OUT = where the results go, CASE = the
# case. Writes <case>.input.brep, <case>.brep (when there is a shape) and
# <case>.json: kind (valid, invalid or refused), volume, message, the input's
# bounding box. One case per process: a build that dies on a case (#474's
# before) loses that case only, and make_pictures.sh records it as a crash.
import json
import os
import sys

sys.path.insert(0, os.environ["DRAFT_TOOLS"])
import FreeCAD as App
import Part
from cases import CASES, DOCS, PRE_ANGLE, SHAPES

OUT = os.environ["OUT"]
NAME = os.environ["CASE"]
os.makedirs(OUT, exist_ok=True)
App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part").SetBool("ImmutableShapeValues", False)


def emit(s):
    os.write(1, (s + "\n").encode())


def pick(shape, which):
    if isinstance(which, int):
        return which
    hits = [i for i, f in enumerate(shape.Faces, 1) if which(f)]
    if len(hits) != 1:
        raise RuntimeError("picked %d faces" % len(hits))
    return hits[0]


def result(feature, inp):
    b = inp.BoundBox
    d = {"bbox": [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax], "input_volume": inp.Volume}
    states = [str(s) for s in feature.State]
    s = feature.Shape
    if "Invalid" in states or "Error" in states or s.isNull():
        msg = feature.getStatusString() if hasattr(feature, "getStatusString") else ""
        d.update(kind="refused", volume=None, message=msg.strip())
    else:
        s.exportBrep(os.path.join(OUT, NAME + ".brep"))
        d.update(kind="valid" if s.isValid() else "invalid", volume=s.Volume, message="")
    return d


st, sk, face, neutral, angle, focus, zoom, eye, note = CASES[NAME]
if sk.startswith("doc:"):
    path, obj = DOCS[sk]
    doc = App.openDocument(path)
    o = doc.getObject(obj)
    inp = o.BaseFeature.Shape
    inp.exportBrep(os.path.join(OUT, NAME + ".input.brep"))
    o.touch()
    o.recompute()
    d = result(o, inp)
else:
    doc = App.newDocument("pic")
    shape = SHAPES[sk]()
    base = doc.addObject("Part::Feature", "Base")
    base.Shape = shape
    body = doc.addObject("PartDesign::Body", "Body")
    body.BaseFeature = base
    doc.recompute()
    base.Shape.exportBrep(os.path.join(OUT, NAME + ".input.brep"))
    dr = body.newObject("PartDesign::Draft", "Draft")
    dr.Base = (body.BaseFeature, ["Face%d" % pick(shape, face)])
    dr.NeutralPlane = (body.BaseFeature, ["Face%d" % pick(shape, neutral)])
    if NAME in PRE_ANGLE:
        dr.Angle = PRE_ANGLE[NAME]
        doc.recompute()
    dr.Angle = angle
    doc.recompute()
    d = result(dr, base.Shape)
json.dump(d, open(os.path.join(OUT, NAME + ".json"), "w"), indent=1)
emit("%-28s %s %s" % (NAME, d["kind"], d["message"] or ("vol=%.4f" % d["volume"])))
emit("DONE")
os._exit(0)
