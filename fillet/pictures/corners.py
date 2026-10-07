# corners.py -- the pictures of fcad docs/CornerBlending.md (setback corners).
#
#   FreeCADCmd corners.py        env OUT: fillet every column of every case
#   python corners.py jobs       write $CORNER_WORK/jobs.json
#   python corners.py <outdir>   one PNG per case
#
# A case is a row of columns, each the same fillet with other corner
# settings (or the fallback off), seen the same way, the corner patches
# orange. Driven by make_corners.sh.
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "models")
P = os.environ.get("CORNER_WORK", "/tmp/corner-pictures")
SIZE = (330, 300)
C_PATCH = (0.95, 0.6, 0.2)
BOX = (10, 10, 10)


def _box():
    import Part
    return Part.makeBox(10, 10, 10)


def _p876():
    import Part
    return Part.read(os.path.join(MODELS, "issue876_fillet_base.brep"))


SHAPES = {"box": _box, "p876": _p876}
# By the corner: every edge ending there, its far end named for the
# per-edge setbacks (x, y or z for the box's three).
BOX_EDGES = {"x": (0, 10, 10), "y": (10, 0, 10), "z": (10, 10, 0)}
# The box's faces at the corner, by their normal, for the faces' depths
BOX_FACES = {"fx": (1, 0, 0), "fy": (0, 1, 0), "fz": (0, 0, 1)}
P876 = (17, 16.75, 3)
P876_EDGES = [(17, 16.75, 0), (-17, 16.75, 3), (19.238761, 15.746985, 3), (17, 16.442791, 20.6)]

# name: shape, corner, the far ends of the filleted edges, radius, view (eye,
# center, height), columns [(label, corners, fallback)], title, note.
# corners: None, a setback, or (setback, {far end: setback}); fallback: the
# FilletCornerSetbackFallback multiple (None: as set, 0: off).
CASES = {
    "box_setbacks": ("box", BOX, ["x", "y", "z"], 1.0, ((1, 0.8, 0.9), (8.6, 8.6, 8.6), 7.5),
                     [("no setback", None, None), ("setback 0", 0, None),
                      ("setback 2", 2, None), ("setback 4", 4, None)],
                     "A box corner, three fillets r 1",
                     "today's corner (a sphere), then set back 0, 2 and 4 along every edge"),
    "box_by_edge": ("box", BOX, ["x", "y", "z"], 1.0, ((1, 0.8, 0.9), (8.6, 8.6, 8.6), 7.5),
                    [("setback 2", 2, None),
                     ("3, 1.5 and 2 by edge", (-1, {"x": 3, "y": 1.5, "z": 2}), None),
                     ("3 and 1.5, the third at d0", (-1, {"x": 3, "y": 1.5}), None)],
                    "Setbacks by edge",
                    "each fillet stopped at its own distance; with one at d0 the patch "
                    "turns tight there"),
    "box_sharp_edge": ("box", BOX, ["x", "y"], 1.0, ((1, 0.8, 0.9), (8.6, 8.6, 8.6), 7.5),
                       [("no setback", None, None), ("setback 2", 2, None),
                        ("setback 4", 4, None)],
                       "Two fillets and a sharp edge",
                       "the patch cuts the sharp edge as far back as the fillets beside it"),
    "box_depth": ("box", BOX, ["x", "y", "z"], 1.0, ((1, 0.8, 0.9), (8.6, 8.6, 8.6), 7.5),
                  [("setback 4", 4, None),
                   ("top face depth 0.5", (4, {"fz": 0.5}), None),
                   ("top face depth 1", (4, {"fz": 1}), None),
                   ("top face depth 2", (4, {"fz": 2}), None)],
                  "A face's depth",
                  "set back 4, the patch's boundary on the top face bowing 0.5, 1 and 2 "
                  "from its chord"),
    "fallback_876": ("p876", P876, P876_EDGES, 1.0, ((0.6, 1, 0.7), P876, 9),
                     [("fallback off", None, 0), ("fallback on (2 x r)", None, 2)],
                     "The fallback: #876's corner (17, 16.75, 3), r 1",
                     "four fillets the corner code fails on; set back where they meet, the "
                     "corner is made"),
}


def _vertex(shape, p):
    import FreeCAD as App
    return [v for v in shape.Vertexes if v.Point.isEqual(App.Vector(*p), 1e-6)][0]


def _face(shape, corner, normal):
    import FreeCAD as App
    P, N = App.Vector(*corner), App.Vector(*normal)
    for f in shape.Faces:
        if f.isInside(P, 1e-6, True):
            u, v = f.Surface.parameter(P)
            if f.normalAt(u, v).isEqual(N, 1e-6):
                return f
    raise ValueError("no face %s at %s" % (normal, corner))


def _edge(shape, a, b):
    import FreeCAD as App
    A, B = App.Vector(*a), App.Vector(*b)
    for e in shape.Edges:
        ps = [v.Point for v in e.Vertexes]
        if len(ps) == 2 and ((ps[0].isEqual(A, 1e-6) and ps[1].isEqual(B, 1e-6))
                             or (ps[0].isEqual(B, 1e-6) and ps[1].isEqual(A, 1e-6))):
            return e
    raise ValueError("no edge %s %s" % (a, b))


def compute():
    import FreeCAD as App
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part")
    had = "FilletCornerSetbackFallback" in params.GetFloats()
    kept = params.GetFloat("FilletCornerSetbackFallback", 2.0)
    out = os.environ["OUT"]
    os.makedirs(out, exist_ok=True)
    # through a document, so that the result's faces are named: a corner's
    # patch is generated from its vertex
    doc = App.newDocument("corners")
    for name, (sk, corner, ends, radius, view, cols, title, note) in CASES.items():
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = SHAPES[sk]()
        doc.recompute()
        shape = obj.Shape
        shape.exportBrep(os.path.join(out, name + ".input.brep"))
        far = {k: BOX_EDGES[k] if isinstance(k, str) else k for k in ends}
        edges = {k: _edge(shape, corner, p) for k, p in far.items()}
        vertex = _vertex(shape, corner)
        for ci, (label, corners, fallback) in enumerate(cols):
            if fallback is not None:
                params.SetFloat("FilletCornerSetbackFallback", float(fallback))
            setting = None
            if isinstance(corners, tuple):
                setting = {vertex: (corners[0], [(edges[k] if k in edges
                                                  else _face(shape, corner, BOX_FACES[k]), d)
                                                 for k, d in corners[1].items()])}
            elif corners is not None:
                setting = {vertex: corners}
            res = {}
            stem = os.path.join(out, "%s.%d" % (name, ci))
            try:
                r = shape.makeFillet(radius, list(edges.values()), corners=setting)
                r.exportBrep(stem + ".brep")
                # the corner patches, each generated from its vertex
                patch = [i for i in range(len(r.Faces))
                         if r.getElementMappedName("Face%d" % (i + 1)).startswith("Vertex")]
                res.update(kind="valid" if r.isValid() else "invalid", volume=r.Volume,
                           tolerance=r.getTolerance(1), patch=patch, faces=len(r.Faces))
            except Exception as e:
                # the exception's class, OCCT's message is too long for a caption
                msg = str(e).strip().splitlines()[-1]
                words = [w for w in msg.split() if "Standard_" in w or "Error" in w]
                res.update(kind="refused", message=words[0].lstrip("0123456789") if words
                           else msg[:30])
            json.dump(res, open(stem + ".json", "w"))
            os.write(1, ("%s %d %s\n" % (name, ci, res)).encode())
    if had:
        params.SetFloat("FilletCornerSetbackFallback", kept)
    else:
        params.RemFloat("FilletCornerSetbackFallback")
    os.write(1, b"DONE\n")
    os._exit(0)


def jobs():
    panels = []
    os.makedirs(P + "/png", exist_ok=True)
    for name, (sk, corner, ends, radius, view, cols, title, note) in CASES.items():
        eye, center, height = view
        for ci in range(len(cols)):
            stem = "%s/r/%s.%d" % (P, name, ci)
            got = os.path.exists(stem + ".brep")
            res = json.load(open(stem + ".json"))
            fc = {i: C_PATCH for i in res["patch"]} if got else {}
            panels.append(dict(brep=stem + ".brep" if got else "%s/r/%s.input.brep" % (P, name),
                               ghost=not got, mark=got, eye=list(eye), center=list(center),
                               height=height, facecolors=fc,
                               png="%s/png/%s.%d.png" % (P, name, ci)))
    json.dump(dict(size=list(SIZE), panels=panels), open(P + "/jobs.json", "w"), indent=0)
    print(len(panels), "panels")


def compose(out):
    import glob
    from PIL import Image, ImageDraw, ImageFont

    def font(bold):
        n = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        for d in ["/usr/share/fonts/truetype/dejavu/"] + glob.glob(
                sys.prefix + "/lib/python3*/site-packages/matplotlib/mpl-data/fonts/ttf/"):
            if os.path.exists(d + n):
                return d + n
        raise SystemExit("no " + n)

    F, FB, FT = (ImageFont.truetype(font(False), 15), ImageFont.truetype(font(True), 16),
                 ImageFont.truetype(font(True), 19))
    GREEN, RED, BLUE = (20, 120, 40), (190, 30, 30), (40, 80, 150)
    os.makedirs(out, exist_ok=True)
    W, H = SIZE
    for name, (sk, corner, ends, radius, view, cols, title, note) in CASES.items():
        n = len(cols)
        top, lab = 64, 84
        img = Image.new("RGB", (max(n * W, 2 * W), top + lab + H), "white")
        d = ImageDraw.Draw(img)
        d.text((10, 8), title, font=FT, fill=(0, 0, 0))
        d.text((10, 34), note, font=F, fill=(60, 60, 60))
        for ci, (label, corners, fallback) in enumerate(cols):
            x = ci * W
            res = json.load(open("%s/r/%s.%d.json" % (P, name, ci)))
            d.text((x + 10, top), label, font=FB, fill=(0, 0, 0))
            if res["kind"] == "refused":
                lines = [("refused: " + res["message"], BLUE)]
            else:
                lines = [("%s, volume %.4f" % (res["kind"], res["volume"]),
                          GREEN if res["kind"] == "valid" else RED),
                         ("tolerance %.1e" % res["tolerance"], (60, 60, 60))]
            for li, (t, colr) in enumerate(lines):
                d.text((x + 10, top + 21 + li * 19), t, font=F, fill=colr)
            img.paste(Image.open("%s/png/%s.%d.png" % (P, name, ci)).convert("RGB"),
                      (x, top + lab))
            if ci:
                d.line([(x, top), (x, top + lab + H)], fill=(170, 170, 170), width=1)
        img.save(os.path.join(out, name + ".png"), optimize=True)
        print(name, os.path.getsize(os.path.join(out, name + ".png")))


# FreeCADCmd imports the file under its own name: OUT says to compute.
# Plain python runs it as __main__, an import does neither.
if "OUT" in os.environ:
    compute()
elif __name__ == "__main__" and len(sys.argv) > 1:
    if sys.argv[1] == "jobs":
        jobs()
    else:
        compose(sys.argv[1])
