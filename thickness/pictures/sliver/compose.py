# compose.py -- the figure, from render.py's four views and a plan worked out
# here: $OUT/arc_join_sliver.png. Needs Pillow, numpy and the DejaVu fonts.
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
D = os.environ.get("OUT") or os.path.dirname(os.path.abspath(__file__))
meta = json.load(open(D + "/meta.json"))
FD = "/usr/share/fonts/truetype/dejavu/"
F = ImageFont.truetype(FD + "DejaVuSans.ttf", 17)
FS = ImageFont.truetype(FD + "DejaVuSans.ttf", 15)
FB = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 18)
FT = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 23)
INK, MUTED, RED = (29, 36, 48), (90, 101, 117), (200, 30, 30)
R, t = 5.0, 0.5
W, H = meta["W"], meta["H"]
def proj(name, p):
    s = meta["shots"][name]; c = np.array(s["center"]); x = np.array(s["x"]); y = np.array(s["y"])
    d = np.array(p) - c
    return (W / 2 + d.dot(x) / s["height"] * H, H / 2 - d.dot(y) / s["height"] * H)
def label(dr, xy, text, anchor, font=FS, fill=INK, to=None):
    if to is not None:
        dr.line([xy, to], fill=fill, width=1)
        dr.ellipse([to[0] - 3, to[1] - 3, to[0] + 3, to[1] + 3], fill=fill)
    box = dr.textbbox(xy, text, font=font, anchor=anchor)
    dr.rectangle([box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3], fill=(255, 255, 255))
    dr.text(xy, text, font=font, fill=fill, anchor=anchor)
def panel3d(name, labels, ring):
    im = Image.open("%s/%s.png" % (D, name)).convert("RGB"); dr = ImageDraw.Draw(im)
    for p, r in ring:
        q = proj(name, p)
        dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=RED, width=3)
    for text, at, p, anchor in labels:
        label(dr, at, text, anchor, to=proj(name, p))
    return im
sl = meta["sliver"]
whole = panel3d("whole", [
    ("the tube round the tangent edge", (640, 150), (5.25 * math.cos(1.0), 5.25 * math.sin(1.0), 0.42), "ls"),
    ("the kept dome's offset", (700, 600), (3.2, 2.5, -4.0), "ms"),
    ("the flat's offset (y = -t)", (250, 600), (-1.5, -0.5, -1.5), "ms"),
    ("the flat's slab, cut by the removed dome's sphere", (30, 60), (-1.0, -0.25, math.sqrt(25 - 1.0625)), "ls"),
    ("a sliver at each end", (760, 250), sl, "ms"),
], [(sl, 16), ([-sl[0], sl[1], 0], 16)])
end = panel3d("end", [
    ("the tube round the tangent edge", (880, 40), (5.25 * math.cos(0.14), 5.25 * math.sin(0.14), 0.42), "rs"),
    ("the ball round the edge's end", (880, 330), (5.33, -0.2, 0.33), "rs"),
    ("the quarter tube round the flat's rim", (880, 600), (5.36, -0.27, -0.5), "rs"),
    ("the flat's slab, cut by the sphere", (20, 60), (4.93, -0.25, math.sqrt(25 - 0.0625 - 4.93 ** 2)), "ls"),
    ("the flat's offset (y = -t)", (20, 600), (4.5, -0.5, -0.5), "ls"),
    ("the sliver", (300, 470), sl, "rs"),
], [(sl, 14)])
# plan at z = 0: what stands just above the plane, and what just below it
def plan(x0, x1, y0, y1, w, h, ss=3):
    X, Y = np.meshgrid(np.linspace(x0, x1, w * ss), np.linspace(y1, y0, h * ss))
    rho = np.hypot(X, Y)
    slab = (Y <= 0) & (Y >= -t)
    C = slab & (rho <= R)
    Dd = (Y <= 0) & ((X - R) ** 2 + Y ** 2 <= t * t)
    E = (Y > 0) & (rho >= R) & (rho <= R + t)
    low = (slab & (np.abs(X) <= R + np.sqrt(np.clip(t * t - Y * Y, 0, None)))) | ((Y > 0) & (rho >= R) & (rho <= R + t))
    img = np.full(X.shape + (3,), 255, np.uint8)
    img[low] = (214, 60, 60)          # below only: the sliver
    img[C] = (150, 170, 196)
    img[Dd & ~C] = (188, 201, 219)
    img[E] = (122, 143, 172)
    return Image.fromarray(img).resize((w, h), Image.LANCZOS)
def px(x, y, x0, x1, y0, y1, w, h): return ((x - x0) / (x1 - x0) * w, (y1 - y) / (y1 - y0) * h)
PW, PH = 900, 520
a = (4.25, 5.75, -0.62, 0.2467)       # equal scale: 1.5 wide on 900, 0.8667 high on 520
pa = plan(*a, PW, PH); da = ImageDraw.Draw(pa)
g = lambda x, y: px(x, y, *a, PW, PH)
label(da, (30, 40), "the tube round the tangent edge", "ls", to=g(5.25 * math.cos(0.025), 5.25 * math.sin(0.025)))
label(da, (30, 300), "the flat's slab, cut by the removed dome's sphere", "ls", to=g(4.6, -0.25))
label(da, (880, 300), "the ball round the edge's end", "rs", to=g(5.3, -0.2))
label(da, (880, 500), "the sliver", "rs", fill=RED, to=g(4.99, -0.4999))
label(da, (30, 500), "the flat's offset, y = -t", "ls", to=g(4.5, -0.5))
zb = (4.9685, 5.003, -0.50022, -0.49900)
pb = plan(*zb, PW, PH); db = ImageDraw.Draw(pb)
g = lambda x, y: px(x, y, *zb, PW, PH)
ya = -0.50007
db.line([g(4.975, ya), g(5.0, ya)], fill=INK, width=2)
for xx in (4.975, 5.0): db.line([g(xx, ya - 0.00002), g(xx, ya + 0.00002)], fill=INK, width=2)
label(db, g(4.9875, ya - 0.00004), "0.025 = t^2 / 2R", "mt")
xa = 4.9742
db.line([g(xa, -0.5), g(xa, -0.499375)], fill=INK, width=2)
for yy in (-0.5, -0.499375): db.line([(g(xa, yy)[0] - 6, g(xa, yy)[1]), (g(xa, yy)[0] + 6, g(xa, yy)[1])], fill=INK, width=2)
label(db, (g(xa, -0.4997)[0] - 10, g(xa, -0.4997)[1]), "0.0006", "rm")
label(db, (30, 60), "the flat's slab, cut by the sphere", "ls", to=g(4.9715, -0.4994))
label(db, (880, 60), "the ball round the edge's end", "rs", to=g(4.992, -0.4994))
label(db, (880, 330), "the sliver: area 5.2e-6; three edges, two of them tangent at the tip", "rs", fill=RED, to=g(4.981, -0.49985))
caps = [("The exact answer, from the removed dome's side", whole), ("One end of the tangent edge", end),
        ("Plan at z = 0: what stands above; red lies only below", pa),
        ("The sliver, y stretched %d times" % round((PH / (zb[3] - zb[2])) / (PW / (zb[1] - zb[0]))), pb)]
M, CAP, TOP = 16, 34, 92
out = Image.new("RGB", (2 * PW + 3 * M, TOP + 2 * CAP + H + PH + 3 * M), (255, 255, 255)); do = ImageDraw.Draw(out)
do.text((M, 14), "The Arc join's sliver face (Thickness.md sec 23)", font=FT, fill=INK)
do.text((M, 50), "Half a ball of radius 5, its sphere in two domes, the dome z > 0 removed, outward 0.5, Arc join: the exact answer "
        "built from primitives, valid, volume 89.1639 (hand value 89.1638), 12 faces.", font=F, fill=MUTED)
pos = [(M, TOP), (PW + 2 * M, TOP), (M, TOP + CAP + H + M), (PW + 2 * M, TOP + CAP + H + M)]
for (cap, im), (x, y) in zip(caps, pos):
    do.text((x, y + 6), cap, font=FB if len(cap) < 60 else FS, fill=INK)
    out.paste(im, (x, y + CAP)); do.rectangle([x, y + CAP, x + im.size[0] - 1, y + CAP + im.size[1] - 1], outline=(200, 206, 215))
out.save(D + "/arc_join_sliver.png"); print(out.size)
