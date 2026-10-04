# python compose.py jobs | <outdir> [names...] -- the render jobs, and one PNG per case.
#
#   python compose.py jobs            write $DRAFT_WORK/jobs.json
#   python compose.py <outdir> [names...]
#
# Four columns -- the draft asked for (the input: the face drafted orange,
# where it goes translucent orange, the neutral face green, the hinge a thick
# line, the pull direction a blue arrow), upstream ($DRAFT_WORK/r/up), the
# fork before the case's fix (r/<stage>), the fork now (r/after) -- and two
# rows: the whole shape and a zoom -- on the faces in the draft column, on the
# case's focus in the others. A draft that gave no
# shape (refused, or FreeCAD died) shows its input, greyed. Needs Pillow (the FreeCAD conda
# env has it) and the DejaVu fonts (matplotlib's copy on macOS).
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cases import CASES, NAMES, STAGES, ZOOM_EYE

P = os.environ["DRAFT_WORK"]
SIZE = (360, 300)
# the draft column's colours, 0-1 for the renderer
C_FACE, C_NEUTRAL, C_HINGE, C_PULL = (0.95, 0.55, 0.1), (0.3, 0.7, 0.35), (0.05, 0.3, 0.1), (0.15, 0.4, 0.9)


def res(col, name):
    f = P + "/r/%s/%s.json" % (col, name)
    return json.load(open(f)) if os.path.exists(f) else {"kind": "missing", "volume": None,
                                                          "message": ""}


def cols(name):
    st = CASES[name][0]
    return [("up", "up"), ("before", st), ("after", "after")]


if sys.argv[1] == "jobs":
    panels = []
    os.makedirs(P + "/png", exist_ok=True)
    for name, (st, sk, face, neutral, angle, focus, zoom, eye, note) in CASES.items():
        inp = P + "/r/after/%s.input.brep" % name
        b = res("after", name)["bbox"]
        center = [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2]
        height = 0.95 * math.sqrt((b[3] - b[0]) ** 2 + (b[4] - b[1]) ** 2 + (b[5] - b[2]) ** 2)
        su = json.load(open(P + "/r/after/%s.setup.json" % name))
        a = P + "/r/after/" + name
        extras = [dict(brep=a + ".face.brep", color=C_FACE, linewidth=2),
                  dict(brep=a + ".neutral.brep", color=C_NEUTRAL, linewidth=2),
                  dict(brep=a + ".drafted.brep", color=C_FACE, transparency=55, linewidth=2.5),
                  dict(brep=a + ".hinge.brep", color=C_HINGE, linewidth=6),
                  dict(brep=a + ".pull.brep", color=C_PULL, linewidth=1)]
        for row, (c, h, e) in enumerate(((center, height, eye),
                                         (su["zoom"]["center"], su["zoom"]["height"], eye))):
            # the part see-through, so a face inside it (a slot's wall) shows
            panels.append(dict(brep=inp, ghost=True, mark=False, eye=list(e), center=c,
                               height=h, extras=extras,
                               png=P + "/png/%s.setup.%d.png" % (name, row)))
        for v, k in cols(name):
            f = P + "/r/%s/%s.brep" % (k, name)
            ghost = not os.path.exists(f)
            for row, (c, h, e) in enumerate(((center, height, eye),
                                             (list(focus), zoom, ZOOM_EYE.get(name, eye)))):
                panels.append(dict(brep=inp if ghost else f, ghost=ghost, mark=not ghost,
                                   eye=list(e), center=c, height=h,
                                   png=P + "/png/%s.%s.%d.png" % (name, v, row)))
    json.dump(dict(size=list(SIZE), panels=panels), open(P + "/jobs.json", "w"), indent=0)
    print(len(panels), "panels")
    sys.exit(0)

from PIL import Image, ImageDraw, ImageFont


def font(bold):
    n = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in ["/usr/share/fonts/truetype/dejavu/"] + glob.glob(
            sys.prefix + "/lib/python3*/site-packages/matplotlib/mpl-data/fonts/ttf/"):
        if os.path.exists(d + n):
            return d + n
    raise SystemExit("no " + n)


F = ImageFont.truetype(font(False), 15)
FB = ImageFont.truetype(font(True), 16)
FT = ImageFont.truetype(font(True), 19)
GREEN, RED, BLUE = (20, 120, 40), (190, 30, 30), (40, 80, 150)


def status(d):
    k = d["kind"]
    if k == "valid":
        return "valid, volume %.4f" % d["volume"], GREEN
    if k == "invalid":
        return "INVALID, volume %.4f" % d["volume"], RED
    if k == "refused":
        m = d["message"].replace("Failed to create draft:", "").replace("BRep_API: ", "").strip()
        return "refused" + (": " + m if m else ""), BLUE
    if k == "crash":
        return "FreeCAD died (segmentation fault)", RED
    return k, RED


def axis_name(v):
    """+X, -Z, or the vector."""
    for i, ax in enumerate("XYZ"):
        if abs(abs(v[i]) - 1) < 1e-6:
            return ("+" if v[i] > 0 else "-") + ax
    return "(%.3f, %.3f, %.3f)" % tuple(v)


def wrap(d, text, width, fnt):
    words, line, lines = text.split(" "), "", []
    for wd in words:
        if d.textlength(line + " " + wd, font=fnt) > width and line:
            lines.append(line)
            line = wd
        else:
            line = (line + " " + wd).strip()
    lines.append(line)
    return lines


OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
for name in sys.argv[2:] or list(CASES):
    st, sk, face, neutral, angle, focus, zoom, eye, note = CASES[name]
    before, fix = STAGES[st]
    W, H = SIZE
    top, lab = 64, 104
    NC = 4
    img = Image.new("RGB", (NC * W, top + lab + 2 * H), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 8), name, font=FT, fill=(0, 0, 0))
    what = "%s; %s" % (NAMES[sk], note)
    if angle is not None:
        what += ", %g deg" % angle
    for li, t in enumerate(wrap(d, what + "  (fix: %s)" % fix, NC * W - 20, F)[:2]):
        d.text((10, 30 + li * 17), t, font=F, fill=(60, 60, 60))
    # the draft asked for
    su = json.load(open(P + "/r/after/%s.setup.json" % name))
    d.text((10, top), "the draft", font=FB, fill=(0, 0, 0))
    rgb = lambda c: tuple(int(255 * x * 0.85) for x in c)
    d.text((10, top + 21), "face %d, %g deg" % (su["face"], su["angle"]), font=F, fill=rgb(C_FACE))
    d.text((10, top + 40), "neutral plane %s (face %d)" % (su["neutral_plane"], su["neutral"]),
           font=F, fill=rgb(C_NEUTRAL))
    d.text((10, top + 59), "arrow: pull direction %s" % axis_name(su["pull"]), font=F,
           fill=rgb(C_PULL))
    d.text((10, top + 78), "thick line: the hinge", font=F, fill=rgb(C_HINGE))
    for row in (0, 1):
        img.paste(Image.open(P + "/png/%s.setup.%d.png" % (name, row)).convert("RGB"),
                  (0, top + lab + row * H))
    d.text((10, top + lab + 8), "translucent orange: the face drafted", font=F, fill=rgb(C_FACE))
    d.text((10, top + lab + H + 8), "zoomed on the faces", font=F, fill=(110, 110, 110))
    titles = ["upstream OCCT 8.0.1", "fork before (%s)" % before, "fork after"]
    for ci, (v, k) in enumerate(cols(name)):
        x = (ci + 1) * W
        r = res(k, name)
        s, colr = status(r)
        d.text((x + 10, top), titles[ci], font=FB, fill=(0, 0, 0))
        for li, t in enumerate(wrap(d, s, W - 20, F)[:2]):
            d.text((x + 10, top + 21 + li * 19), t, font=F, fill=colr)
        for row in (0, 1):
            pf = P + "/png/%s.%s.%d.png" % (name, v, row)
            img.paste(Image.open(pf).convert("RGB"), (x, top + lab + row * H))
            meta = json.load(open(pf + ".json")) if os.path.exists(pf + ".json") else {}
            if row == 0 and r["kind"] in ("refused", "crash"):
                d.text((x + 10, top + lab + 8), "no shape: the input is shown", font=F,
                       fill=(110, 110, 110))
            if row == 1:
                d.text((x + 10, top + lab + H + 8),
                       "zoomed, from above" if name in ZOOM_EYE else "zoomed", font=F,
                       fill=(110, 110, 110))
            if meta.get("dropped") and row == 0:
                d.text((x + 10, top + lab + 28), "%d face(s) of no area, not drawn" % meta["dropped"],
                       font=F, fill=RED)
            if row == 0 and (meta.get("badedges") or meta.get("badfaces")):
                d.text((x + 10, top + lab + 2 * H - 26 - H),
                       "red: %d edge(s), %d face(s) at fault" % (meta.get("badedges", 0),
                                                                 meta.get("badfaces", 0)),
                       font=F, fill=RED)
    for ci in range(1, NC):
        d.line([(ci * W, top), (ci * W, top + lab + 2 * H)],
               fill=(150, 150, 150) if ci == 1 else (200, 200, 200), width=2 if ci == 1 else 1)
    d.line([(0, top + lab + H), (NC * W, top + lab + H)], fill=(225, 225, 225), width=1)
    img.save(os.path.join(OUT, name + ".png"), optimize=True)
    print(name, os.path.getsize(os.path.join(OUT, name + ".png")))
