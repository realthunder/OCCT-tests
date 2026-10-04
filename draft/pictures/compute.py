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


def setup(shape, fi, ni, angle):
    """What the draft is asked to do, to draw it: the face, the neutral
    plane, the pull direction (the neutral face's plane normal, as
    PartDesign takes it with no pull direction given), the hinge -- the line
    where the face's plane meets the neutral plane -- and the face turned
    about it as Draft_Modification turns a plane (FindRotation, with the
    face's outward normal standing for its orientation in the shape).
    Writes <case>.face.brep, .neutral.brep, .drafted.brep, .hinge.brep and
    .pull.brep."""
    import math
    V = App.Vector
    f, nf = shape.Faces[fi - 1], shape.Faces[ni - 1]
    pull = V(nf.Surface.Axis)
    pull.normalize()
    u0, u1, v0, v1 = f.ParameterRange
    n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    hx = n.cross(pull)
    if hx.Length < 1e-9:
        raise RuntimeError("face parallel to the neutral plane")
    hx.normalize()
    # a point of the hinge: on both planes, nearest the face's centre
    c = f.CenterOfMass
    p0 = V(nf.Surface.Position)
    # move c within the face's plane, along n x hx, onto the neutral plane
    t = n.cross(hx)
    k = (p0 - c).dot(pull) / t.dot(pull)
    h0 = c + t * k
    ny = n.cross(hx)
    a, b, cc = pull.dot(hx), pull.dot(ny), pull.dot(n)
    den = math.sqrt(max(1 - a * a, 0))
    sa = math.sin(math.radians(angle))
    if den <= abs(sa):
        raise RuntimeError("no rotation")
    phi = math.atan2(b / den, cc / den)
    th0 = math.acos(sa / den)
    theta = th0 - phi
    if math.cos(theta) < 0:
        theta = -th0 - phi
    while abs(theta) > math.pi:
        theta += math.pi * (1 if theta < 0 else -1)
    f.exportBrep(os.path.join(OUT, NAME + ".face.brep"))
    nf.exportBrep(os.path.join(OUT, NAME + ".neutral.brep"))
    dr = f.copy()
    dr.rotate(h0, hx, math.degrees(theta))
    dr.exportBrep(os.path.join(OUT, NAME + ".drafted.brep"))
    # the hinge drawn over the face's extent along it, and the neutral face's
    ts = [(v.Point - h0).dot(hx) for v in f.Vertexes + nf.Vertexes]
    Part.Edge(Part.LineSegment(h0 + hx * min(ts), h0 + hx * max(ts))).exportBrep(
        os.path.join(OUT, NAME + ".hinge.brep"))
    # the pull direction: an arrow from the hinge's middle
    diag = shape.BoundBox.DiagonalLength
    m = h0 + hx * ((min(ts) + max(ts)) / 2)
    L, r = 0.15 * diag, 0.01 * diag
    arrow = Part.makeCylinder(r, L, m, pull).fuse(
        Part.makeCone(2.5 * r, 0, 4 * r, m + pull * L, pull))
    arrow.exportBrep(os.path.join(OUT, NAME + ".pull.brep"))
    # the draft column's zoom: the two faces and the face drafted
    bb = f.BoundBox
    bb.add(nf.BoundBox)
    bb.add(dr.BoundBox)
    zoom = {"center": list(bb.Center), "height": 1.1 * bb.DiagonalLength}
    return {"face": fi, "neutral": ni, "angle": angle, "pull": [pull.x, pull.y, pull.z],
            "zoom": zoom,
            "theta": math.degrees(theta), "hinge": [list(h0), [hx.x, hx.y, hx.z]],
            "neutral_plane": "%s" % plane_name(nf)}


def plane_name(f):
    """x=20, or the plane's normal and a point, for the caption."""
    a = f.Surface.Axis
    p = f.Surface.Position
    for i, ax in enumerate("xyz"):
        if abs(abs(a[i]) - 1) < 1e-9:
            return "%s=%g" % (ax, round(p[i], 4))
    return "normal (%.3f, %.3f, %.3f)" % (a.x, a.y, a.z)


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
    fi, ni = pick(shape, face), pick(shape, neutral)
    try:
        su = setup(base.Shape, fi, ni, angle)
    except Exception as e:
        su = {"face": fi, "neutral": ni, "angle": angle, "error": str(e)}
    json.dump(su, open(os.path.join(OUT, NAME + ".setup.json"), "w"), indent=1)
    dr = body.newObject("PartDesign::Draft", "Draft")
    dr.Base = (body.BaseFeature, ["Face%d" % fi])
    dr.NeutralPlane = (body.BaseFeature, ["Face%d" % ni])
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
