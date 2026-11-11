# python3 issue334_arc_reference_compose.py -- lays the two panels of
# issue334_arc_reference_picture.py ($OUT, default here) side by side under
# their captions and writes issue334_arc_reference.png next to this file.
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT", HERE)
def font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()
PANELS = [("stored", "Before: the recompute stops at Pocket005",
           ["its \"up to face\" is not found again, so the body stays",
            "the file's: 47381.9336, invalid (4 faces, red)"]),
          ("recomputed", "After: the whole document recomputes",
           ["45 objects, none left; the body valid and clean by",
            "BOP's check, 48550.1365"])]
W, H, TOP = 900, 800, 120
img = Image.new("RGB", (W * len(PANELS), H + TOP), "white")
draw = ImageDraw.Draw(img)
for i, (name, title, lines) in enumerate(PANELS):
    img.paste(Image.open(os.path.join(OUT, "issue334_%s.png" % name)).convert("RGB"), (W * i, TOP))
    draw.text((W * i + 30, 14), title, fill="black", font=font(30))
    for j, line in enumerate(lines):
        draw.text((W * i + 30, 58 + 28 * j), line, fill=(70, 70, 70), font=font(22))
draw.line((W, 10, W, H + TOP - 10), fill=(200, 200, 200), width=2)
img.save(os.path.join(HERE, "issue334_arc_reference.png"), optimize=True)
