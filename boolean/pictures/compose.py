# compose.py <out dir> -- lays out each picture prep.py listed
# ($W/pictures.json), from the panels render.py drew, into <out dir>/<name>.png.
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


def wrap(d, text, width):
    lines, line = [], ""
    for w in text.split():
        if line and d.textlength(line + " " + w, font=F) > width:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    return lines + [line]


os.makedirs(out, exist_ok=True)
for pic in json.load(open(os.path.join(W, "pictures.json"))):
    panels = pic["panels"]
    P = Image.open(panels[0]["png"]).size[0]
    width = P * len(panels)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    caption = wrap(probe, pic["caption"], width - 20)
    HEAD = 34 + 17 * len(caption) + 12
    TOP, FOOT = 70, 10
    img = Image.new("RGB", (width, HEAD + TOP + P + FOOT), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 8), pic["title"], font=FT, fill=(0, 0, 0))
    for i, t in enumerate(caption):
        d.text((10, 34 + i * 17), t, font=F, fill=(60, 60, 60))
    for i, p in enumerate(panels):
        x = i * P
        d.text((x + 10, HEAD), p["title"], font=FB, fill=(0, 0, 0))
        colr = (190, 30, 30) if p["bad"] else (60, 60, 60)
        for j, t in enumerate(wrap(d, p["note"], P - 20)[:2]):
            d.text((x + 10, HEAD + 22 + j * 18), t, font=F, fill=colr)
        img.paste(Image.open(p["png"]).convert("RGB"), (x, HEAD + TOP))
    path = os.path.join(out, pic["name"] + ".png")
    img.save(path)
    print(path)
