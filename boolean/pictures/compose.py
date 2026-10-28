# compose.py <out dir> -- lays out the panels prep.py listed ($W/panels.json)
# and render.py drew into ../models/pictures/issue064_fuzzy_plane_cylinder.png.
# Needs Pillow and the DejaVu fonts (matplotlib's copy on macOS).
import glob
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W = os.environ.get("W", "/tmp/boolean-pictures")
out = sys.argv[1]


def font(bold):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in ["/usr/share/fonts/truetype/dejavu/"] + glob.glob(
            sys.prefix + "/lib/python3*/site-packages/matplotlib/mpl-data/fonts/ttf/"):
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    raise SystemExit("no DejaVu font")


F, FB, FT = (ImageFont.truetype(font(False), 15), ImageFont.truetype(font(True), 16),
             ImageFont.truetype(font(True), 19))
spec = json.load(open(os.path.join(W, "panels.json")))
panels = spec["panels"]
P = Image.open(panels[0]["png"]).size[0]
HEAD, TOP, FOOT = 64, 70, 10


def wrap(d, text, width):
    lines, line = [], ""
    for w in text.split():
        if line and d.textlength(line + " " + w, font=F) > width:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    return lines + [line]


img = Image.new("RGB", (P * len(panels), HEAD + TOP + P + FOOT), "white")
d = ImageDraw.Draw(img)
d.text((10, 8), "#64: a cylinder split by a plane tilted off its axis (k %g), with a fuzzy value"
       % spec["k"], font=FT, fill=(0, 0, 0))
caption = ("General fuse (BOPAlgo_Builder), the cylinder's seam away from the cut; "
           "the pieces moved apart along the plane's normal, the second in orange.")
for i, t in enumerate(wrap(d, caption, P * len(panels) - 20)):
    d.text((10, 34 + i * 17), t, font=F, fill=(60, 60, 60))
for i, p in enumerate(panels):
    x = i * P
    d.text((x + 10, HEAD), p["title"], font=FB, fill=(0, 0, 0))
    colr = (190, 30, 30) if p["solids"] < 2 else (60, 60, 60)
    for j, t in enumerate(wrap(d, p["note"], P - 20)[:2]):
        d.text((x + 10, HEAD + 22 + j * 18), t, font=F, fill=colr)
    img.paste(Image.open(p["png"]).convert("RGB"), (x, HEAD + TOP))
os.makedirs(out, exist_ok=True)
img.save(os.path.join(out, "issue064_fuzzy_plane_cylinder.png"))
print(os.path.join(out, "issue064_fuzzy_plane_cylinder.png"))
