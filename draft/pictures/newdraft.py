# newdraft.py -- the pictures of fcad docs/NewDraft.md (the cell draft, and
# Auto's checks of the classic draft's result).
#
#   FreeCADCmd newdraft.py        env CASE, COL, OUT: draft one case one way
#   python newdraft.py jobs       write $DRAFT_WORK/newdraft/jobs.json
#   python newdraft.py <outdir>   one PNG per case
#
# Three columns: the draft asked for (the input see-through, the face
# drafted orange, where it goes translucent orange, the neutral face green),
# then the case's two results; two rows, the whole shape and a zoom. In a
# result the faces the draft made are orange (a face matching none of the
# input's), or, with "pieces", every face its own colour. Driven by
# make_newdraft.sh.
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.join(HERE, "..", "..")
P = os.path.join(os.environ.get("DRAFT_WORK", "/tmp/draft-pictures"), "newdraft")
SIZE = (400, 330)
C_FACE, C_NEUTRAL, C_MADE = (0.95, 0.55, 0.1), (0.3, 0.7, 0.35), (0.95, 0.6, 0.2)
C_CROSS = (0.85, 0.15, 0.15)


def _plane_at(axis, value, lo=None, hi=None):
    def pick(f):
        if f.Surface.__class__.__name__ != "Plane":
            return False
        b = f.BoundBox
        if abs(getattr(b, axis + "Min") - value) > 1e-9:
            return False
        if abs(getattr(b, axis + "Max") - value) > 1e-9:
            return False
        return lo is None or (b.XMin > lo - 1e-9 and b.XMax < hi + 1e-9)
    return pick


def _ribs():
    # TestDraft.testDraftAutoCrossesRib
    import FreeCAD as App
    import Part
    V = App.Vector
    return Part.makeBox(20, 10, 2).fuse([Part.makeBox(2, 6, 10, V(0, 2, 2)),
                                         Part.makeBox(2, 6, 10, V(5, 2, 2))]).removeSplitter()


def _step():
    # TestDraft.testDraftAutoStopAtBody
    import FreeCAD as App
    import Part
    V = App.Vector
    return Part.makeBox(20, 10, 10).cut(Part.makeBox(20, 5, 5, V(0, 0, 5))).removeSplitter()


def _rbox(sharp=False):
    # TestDraft.testDraftNewTangentChain: a block, its vertical edges
    # filleted; with sharp, the one at the origin left sharp
    # (testDraftNewTangentChainSharpCorner)
    import Part
    s = Part.makeBox(20, 10, 10)
    return s.makeFillet(2, [e for e in s.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1
                            and (not sharp or abs(e.Vertexes[0].X) + abs(e.Vertexes[0].Y) > 1e-9)])


def _pocket():
    # TestDraft.testDraftAutoTangentChainBreaksThrough: a pocket with rounded
    # corners 2 behind a block's front
    import FreeCAD as App
    import Part
    V = App.Vector
    prof = Part.makeBox(20, 10, 16, V(10, 2, 4))
    prof = prof.makeFillet(2, [e for e in prof.Edges
                               if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1])
    return Part.makeBox(40, 30, 20).cut(prof).removeSplitter()


def _chamfer():
    # the suite's new_roof_chamfer_*: the block with its corner (20, 10) cut
    # by a 45 deg wall of 6 x 6, the five vertical edges filleted 1
    import FreeCAD as App
    import Part
    V = App.Vector
    pts = [V(0, 0, 0), V(20, 0, 0), V(20, 4, 0), V(14, 10, 0), V(0, 10, 0), V(0, 0, 0)]
    s = Part.Face(Part.makePolygon(pts)).extrude(V(0, 0, 10))
    return s.makeFillet(1, [e for e in s.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1])


def _tbox():
    # TestDraft.testDraftFilletAcrossPull: a block, the top edge of its end
    # wall x=20 filleted 2
    import Part
    s = Part.makeBox(20, 10, 10)
    return s.makeFillet(2, [e for e in s.Edges if abs(e.BoundBox.XMin - 20) < 1e-9
                            and abs(e.BoundBox.XMax - 20) < 1e-9
                            and abs(e.BoundBox.ZMin - 10) < 1e-9])


def _brep(*path):
    def make():
        import Part
        return Part.read(os.path.join(FORK, *path))
    return make


SHAPES = {
    "ribs": _ribs,
    "step": _step,
    "issue962_pocket002": _brep("fillet", "models", "issue962_pocket002.brep"),
    "issue309_shape": _brep("draft", "models", "issue309_shape.brep"),
    "issue876_fillet": _brep("fillet", "models", "issue876_fillet_base.brep"),
    "rbox": _rbox,
    "rbox_sharp": lambda: _rbox(sharp=True),
    "pocket": _pocket,
    "chamfer": _chamfer,
    "tbox": _tbox,
}
CLASSIC = ("Classic", dict(Method="Classic"), "the classic draft")
AUTO = ("Auto", dict(Method="Auto"), "Auto (the checks, then the cell draft)")
NEW = ("New", dict(Method="New"), "the cell draft")
# name: shape, face, neutral, angle, reversed, columns, eye, the second row
# ((eye or None for the case's, center, height), or "classic": the whole
# classic result), pieces, title, note
CASES = {
    "auto_ribs_a20": ("ribs", _plane_at("X", 2), _plane_at("Z", 2), 20, True, [CLASSIC, AUTO],
                      (0.55, -1, 0.5), ((0, -1, 0), (4.5, 5, 7), 12), False,
                      "Two ribs 3 apart (TestDraft)",
                      "the first rib's inner face, drafted out at 20 deg about the plate, leans "
                      "3.64 into the second rib"),
    "auto_step_a60": ("step", _plane_at("Z", 5), _plane_at("Y", 5), 60, False, [CLASSIC, AUTO],
                      (0.7, -1.4, 0.8), ((1, 0, 0), (10, 5, 7), 17), False,
                      "A step, its ledge drafted past the top (TestDraft)",
                      "the ledge z=5 drafted about the step's wall at 60 deg rises 8.66 at its "
                      "front, past the top at 10; StopAtBody on"),
    "auto_issue962_f43_n30_a15": ("issue962_pocket002", 43, 30, 15, False, [CLASSIC, AUTO],
                                  (-1, -1.6, 1.2), (None, "crossing"), False,
                                  "#962's ribs, face 43 at 15 deg",
                                  "the classic draft's result is valid but crosses itself; the "
                                  "cell draft fuses what it runs into"),
    "auto_issue309_f2_n9_a60": ("issue309_shape", 2, 9, 60, False, [CLASSIC, AUTO],
                                (-1, -1.6, 1.2), "classic", False,
                                "#309, face 2 at 60 deg",
                                "the classic draft grows a fin many times the part; StopAtBody on"),
    "cones_issue876_f44_n36_a15": ("issue876_fillet", 44, 36, 15, False,
                                   [("before", dict(Method="New"),
                                     "the cell draft, cone tool from the apex"),
                                    ("New", dict(Method="New"),
                                     "the cell draft, cone tool on the face's cone")],
                                   (0.6, -1, -0.9), (None, (-15, -12, 18), 14), True,
                                   "#876's roof under its lid",
                                   "the cavity's roof drafted 15 deg about a wall; every face its "
                                   "own colour, to show the corner cones put back together"),
    # section 13: tangent chains
    "chain_rbox_a5": ("rbox", _plane_at("Y", 0), _plane_at("Z", 0), 5, False, [CLASSIC, NEW],
                      (0.7, -1.4, 0.8), (None, (19, 1, 6), 9), False,
                      "A block with rounded corners (TestDraft)",
                      "one wall drafted 5 deg about the floor drafts its tangent chain all "
                      "round: the walls turn, the fillets turn into cones"),
    "chain_pocket_break_a10": ("pocket", _plane_at("Y", 2), _plane_at("Z", 4), 10, False,
                               [CLASSIC, AUTO], (0.6, -1.4, 1.1), (None, (20, 2, 16), 14), False,
                               "A pocket drafted through the front (TestDraft)",
                               "the pocket's front wall drafted out 10 deg about its floor moves "
                               "2.82 at the top, through the 2 thick front wall"),
    "chain_issue962_f57_n29_a5": ("issue962_pocket002", 57, 29, 5, False, [CLASSIC, NEW],
                                  (-0.8, -1.2, 1.2), (None, (42, 22, 27), 16), False,
                                  "#962, face 57 at 5 deg",
                                  "the classic draft drafts the face and the fillet beside it "
                                  "and stops; the cell draft drafts the whole chain"),
    # section 14: past a cone's apex, a sharp corner
    "apex_rbox_a15": ("rbox", _plane_at("Y", 0), _plane_at("Z", 0), 15, False, [CLASSIC, NEW],
                      (0.7, -1.4, 0.8), (None, (19, 1, 6), 9), False,
                      "The block inward at 15 deg",
                      "the fillets' cones reach their apex at 7.46, under the top: above it "
                      "the walls meet in a ridge"),
    "sharp_rbox_a15": ("rbox_sharp", _plane_at("Y", 10), _plane_at("Z", 0), 15, False,
                       [CLASSIC, NEW], (-0.8, -1.4, 0.8), (None, (1, 1, 6), 9), False,
                       "The block with a sharp corner, inward at 15 deg",
                       "the chain closes at the sharp corner (front left): there the two new "
                       "planes meet in a new edge"),
    # section 17: tangent propagation
    "prop_rbox_a15": ("rbox", _plane_at("Y", 0), _plane_at("Z", 0), 15, False,
                      [("New", dict(Method="New"), "tangent propagation on"),
                       ("off", dict(Method="New", TangentPropagation=False),
                        "off: the fillets made again")],
                      (0.7, -1.4, 0.8), (None, (19, 1, 6), 9), False,
                      "One wall of the filleted block at 15 deg, tangent propagation on and off",
                      "on, the wall's tangent chain drafts all round; off, only the wall turns, "
                      "and the fillets beside it are made again along its slope"),
    "prop_rbox_two_a15": ("rbox", [_plane_at("Y", 0), _plane_at("X", 0)], _plane_at("Z", 0),
                          15, False,
                          [("New", dict(Method="New"), "tangent propagation on"),
                           ("off", dict(Method="New", TangentPropagation=False),
                            "off: the fillets made again")],
                          (-0.8, -1.4, 0.8), (None, (1, 1, 6), 9), False,
                          "Two walls of the filleted block at 15 deg, not the fillet between them",
                          "off, the fillet between the two walls is made again where the "
                          "drafted walls meet, at their new angle"),
    # section 18: the roof
    "roof_rbox_a30": ("rbox", _plane_at("Y", 0), _plane_at("Z", 0), 30, False, [CLASSIC, NEW],
                      (0.7, -1.4, 0.8), ((1, 0, 0), (20, 5, 5), 13), False,
                      "The block inward at 30 deg: a hipped roof",
                      "the short walls narrow to nothing at 8.66, under the top at 10, and the "
                      "long walls meet between them; the top is gone"),
    "roof_chamfer_a20": ("chamfer", _plane_at("Y", 0), _plane_at("Z", 0), 20, False,
                         [CLASSIC, NEW], (0.7, -1.4, 0.8), ((0, 0, 1), (10, 5, 5), 24), False,
                         "A block with a corner wall, inward at 20 deg: a roof partway",
                         "the end wall right narrows to nothing at 7.77 and the corner wall "
                         "meets the front wall from there; the top stays, smaller"),
    "roof_pocket_a30": ("pocket", _plane_at("Y", 2), _plane_at("Z", 4), -30, False,
                        [CLASSIC, NEW], (0.6, -1.4, 1.1), ((0, -1, 0), (20, 7, 12), 20), False,
                        "The pocket's walls inward at 30 deg: a hollow (results cut at y = 7)",
                        "the walls meet 8.66 over the floor, under the top: the pocket closes "
                        "over into a hollow inside the block"),
    "roof_rbox_a26": ("rbox", _plane_at("Y", 0), _plane_at("Z", 0), 26, False,
                      [("before", dict(Method="New"), "the cell draft, before"),
                       ("New", dict(Method="New"), "the cell draft, fixed")],
                      (0.7, -1.4, 0.8), (None, (18, 2, 4), 9), False,
                      "The block inward at 26 deg: the cones the wrong way round",
                      "the fillets' tops lie past their apex (4.10); before, each cone face "
                      "went round the long way and the body came out valid, 69 short"),
    # section 19: a fillet across the pull direction
    "across_tbox_a15": ("tbox", _plane_at("X", 20), _plane_at("Z", 0), 15, False,
                        [CLASSIC, NEW], (0.9, -1.4, 0.7), ((0, -1, 0), (18, 5, 8), 8), False,
                        "A fillet across the pull direction (TestDraft)",
                        "the end wall drafted 15 deg about the floor; its top edge's fillet, "
                        "along y, is taken off and made again where the wall meets the top"),
    "across_issue962_f30_n25_a15": ("issue962_pocket002", 30, 25, 15, False, [CLASSIC, NEW],
                                    (1, -1.2, 0.9), ((1, -0.6, 0.5), (47, 18.7, 24), 20), False,
                                    "#962, face 30 at 15 deg",
                                    "the wall x=50 drafted about a slot's floor; the r=7 "
                                    "fillets along its top, cut by the slots, made again "
                                    "onto the sloped top"),
}

# A result shown cut, its back half kept (a hollow inside it): axis, value. Its
# volume and checks are the whole result's.
CUT = {"roof_pocket_a30": ("y", 7)}

# NEWDRAFT_ONLY: the cases to make (space separated), the others left as they are
if os.environ.get("NEWDRAFT_ONLY"):
    CASES = {k: v for k, v in CASES.items() if k in os.environ["NEWDRAFT_ONLY"].split()}


def compute():
    import FreeCAD as App
    import Part
    name, col, out = os.environ["CASE"], os.environ["COL"], os.environ["OUT"]
    os.makedirs(out, exist_ok=True)
    sk, face, neutral, angle, rev, cols, eye, zoom, pieces, title, note = CASES[name]
    props = [c for c in cols if c[0] == col][0][1]
    shape = SHAPES[sk]()
    pick = lambda w: w if isinstance(w, int) else [i for i, f in enumerate(shape.Faces, 1)
                                                   if w(f)][0]
    # a face, or a list of them drafted together
    fis = [pick(w) for w in face] if isinstance(face, list) else [pick(face)]
    ni = pick(neutral)
    stem = os.path.join(out, "%s.%s" % (name, col))
    shape.exportBrep(os.path.join(out, name + ".input.brep"))
    setup(shape, fis, ni, angle, rev, os.path.join(out, name))
    doc = App.newDocument("pic")
    base = doc.addObject("Part::Feature", "Base")
    base.Shape = shape
    body = doc.addObject("PartDesign::Body", "Body")
    body.BaseFeature = base
    doc.recompute()
    d = body.newObject("PartDesign::Draft", "Draft")
    d.Base = (base, ["Face%d" % i for i in fis])
    d.NeutralPlane = (base, ["Face%d" % ni])
    d.Angle = angle
    d.Reversed = rev
    d.StopAtBody = True
    for k, v in props.items():
        setattr(d, k, v)
    doc.recompute()
    d.touch()
    doc.recompute()
    st = [str(s) for s in d.State]
    r = d.Shape
    res = {}
    if "Invalid" in st or "Error" in st or r.isNull():
        res.update(kind="refused", message=d.getStatusString())
    else:
        r.exportBrep(stem + ".brep")
        try:
            r.check(True)
            bop = "clean"
        except Exception as e:
            bop = "self-intersecting" if "SelfIntersect" in str(e) else "fails"
        # the faces the draft made: matching no face of the input
        def key(f):
            c = f.CenterOfMass
            return (f.Surface.__class__.__name__, round(f.Area, 6), round(c.x, 5),
                    round(c.y, 5), round(c.z, 5))
        keys = {key(f) for f in shape.Faces}
        made = [i for i, f in enumerate(r.Faces) if key(f) not in keys]
        if name in CUT:
            # the back half; its faces on a face the draft made are made
            axis, at = CUT[name]
            b = r.BoundBox
            lo = [b.XMin - 1, b.YMin - 1, b.ZMin - 1]
            size = [b.XLength + 2, b.YLength + 2, b.ZLength + 2]
            k = "xyz".index(axis)
            size[k] -= at - lo[k]
            lo[k] = at
            half = r.common(Part.makeBox(size[0], size[1], size[2], App.Vector(*lo)))
            half.exportBrep(stem + ".brep")
            made = [i for i, f in enumerate(half.Faces)
                    if any(f.common(r.Faces[m]).Area > 0.5 * f.Area for m in made)]
            res.update(shown_faces=len(half.Faces))
        b = r.BoundBox
        res.update(center=list(b.Center), height=0.95 * b.DiagonalLength)
        res.update(kind="valid" if r.isValid() else "invalid", volume=r.Volume,
                   faces=len(r.Faces), bop=bop, made=made)
        if bop != "clean":
            res.update(crossing(r, made))
    res.update(face=fis, neutral=ni, angle=angle, input_faces=len(shape.Faces),
               classic_volume=None)
    json.dump(res, open(stem + ".json", "w"))
    os.write(1, b"DONE\n")
    os._exit(0)


def crossing(r, made):
    """Where a face the draft made crosses another face of the result: their
    section away from the edges they share. The faces (red in the picture)
    and a frame on the section."""
    import FreeCAD as App
    faces, box = set(), App.BoundBox()
    for m in made:
        fm = r.Faces[m]
        for g, fg in enumerate(r.Faces):
            if g == m or not fm.BoundBox.intersect(fg.BoundBox):
                continue
            shared = [e for e in fm.Edges if any(e.isSame(x) for x in fg.Edges)]
            for e in fm.section(fg).Edges:
                p = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
                import Part
                pv = Part.Vertex(p)
                if all(pv.distToShape(x)[0] > 1e-5 for x in shared) and e.Length > 1e-5:
                    faces.update((m, g))
                    box.add(e.BoundBox)
    if not faces:
        return {}
    return {"crossing": sorted(faces), "crossframe": [list(box.Center),
                                                      max(2.5 * box.DiagonalLength, 2.0)]}


def setup(shape, fis, ni, angle, rev, stem):
    """The faces, the neutral face and the faces turned onto their new planes,
    for the draft column: about the line where the face's plane meets the
    neutral plane, the way PartDesign's Draft turns it (pull direction the
    neutral face's normal; the classic draft's FindRotation, as in
    compute.py's setup())."""
    import FreeCAD as App
    import Part
    V = App.Vector
    nf = shape.Faces[ni - 1]
    pull = V(nf.Surface.Axis)
    pull.normalize()
    if rev:
        angle = -angle
    faces, turned = [], []
    for fi in fis:
        f, dr = turn(shape.Faces[fi - 1], nf, pull, angle)
        faces.append(f)
        turned.append(dr)
    f = Part.makeCompound(faces)
    dr = Part.makeCompound(turned)
    f.exportBrep(stem + ".face.brep")
    nf.exportBrep(stem + ".neutral.brep")
    dr.exportBrep(stem + ".drafted.brep")
    bb = f.BoundBox
    bb.add(dr.BoundBox)
    b = shape.BoundBox
    json.dump(dict(zoom=[list(bb.Center), 1.2 * bb.DiagonalLength],
                   whole=[list(b.Center), 0.95 * b.DiagonalLength]),
              open(stem + ".setup.json", "w"))


def turn(f, nf, pull, angle):
    """A face and its copy turned onto its new plane."""
    import FreeCAD as App
    V = App.Vector
    u0, u1, v0, v1 = f.ParameterRange
    n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    hx = n.cross(pull)
    hx.normalize()
    c = f.CenterOfMass
    t = n.cross(hx)
    h0 = c + t * ((V(nf.Surface.Position) - c).dot(pull) / t.dot(pull))
    ny = n.cross(hx)
    a, b, cc = pull.dot(hx), pull.dot(ny), pull.dot(n)
    den = math.sqrt(max(1 - a * a, 0))
    sa = math.sin(math.radians(angle))
    phi = math.atan2(b / den, cc / den)
    th0 = math.acos(sa / den)
    theta = th0 - phi
    if math.cos(theta) < 0:
        theta = -th0 - phi
    while abs(theta) > math.pi:
        theta += math.pi * (1 if theta < 0 else -1)
    dr = f.copy()
    dr.rotate(h0, hx, math.degrees(theta))
    return f, dr


PALETTE = [(0.85, 0.37, 0.35), (0.35, 0.6, 0.85), (0.45, 0.75, 0.4), (0.9, 0.7, 0.3),
           (0.65, 0.45, 0.8), (0.3, 0.75, 0.75), (0.85, 0.5, 0.7), (0.6, 0.6, 0.35)]


def jobs():
    panels = []
    os.makedirs(P + "/png", exist_ok=True)
    for name, (sk, face, neutral, angle, rev, cols, eye, zoom, pieces, title, note) in CASES.items():
        r = P + "/r/" + name
        su = json.load(open(r + ".setup.json"))
        if zoom == "classic":
            cr = json.load(open(r + ".Classic.json"))
            views = [(eye,) + tuple(su["whole"]), (eye, cr["center"], cr["height"])]
        elif zoom[1] == "crossing":
            cr = json.load(open(r + ".Classic.json"))
            views = [(eye,) + tuple(su["whole"]), (zoom[0] or eye,) + tuple(cr["crossframe"])]
        else:
            views = [(eye,) + tuple(su["whole"]), (zoom[0] or eye, zoom[1], zoom[2])]
        extras = [dict(brep=r + ".face.brep", color=C_FACE, linewidth=2),
                  dict(brep=r + ".neutral.brep", color=C_NEUTRAL, linewidth=2),
                  dict(brep=r + ".drafted.brep", color=C_FACE, transparency=55, linewidth=2.5)]
        for row, (e, c, h) in enumerate(views):
            panels.append(dict(brep=r + ".input.brep", ghost=True, mark=False, eye=list(e),
                               center=list(c), height=h, extras=extras,
                               png=P + "/png/%s.setup.%d.png" % (name, row)))
        for col, _, _ in cols:
            res = json.load(open("%s.%s.json" % (r, col)))
            brep = "%s.%s.brep" % (r, col)
            got = os.path.exists(brep)
            fc = {}
            if got and pieces:
                fc = {i: PALETTE[i % len(PALETTE)] for i in range(res["faces"])}
            elif got:
                fc = {i: C_MADE for i in res["made"]}
                fc.update({i: C_CROSS for i in res.get("crossing", [])})
            for row, (e, c, h) in enumerate(views):
                # validity is in the caption; render.py's edge marks would flag
                # #962's nut hole seam, an edge of the input
                panels.append(dict(brep=brep if got else r + ".input.brep", ghost=not got,
                                   mark=False, eye=list(e), center=list(c), height=h,
                                   facecolors=fc,
                                   transparency=35 if got and not pieces else 0,
                                   png=P + "/png/%s.%s.%d.png" % (name, col, row)))
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
    GREEN, RED, BLUE, GREY = (20, 120, 40), (190, 30, 30), (40, 80, 150), (110, 110, 110)
    rgb = lambda c: tuple(int(255 * x * 0.85) for x in c)
    os.makedirs(out, exist_ok=True)
    W, H = SIZE
    for name, (sk, face, neutral, angle, rev, cols, eye, zoom, pieces, title, note) in CASES.items():
        r = P + "/r/" + name
        top, lab = 64, 100
        row2 = ("framed on the classic result" if zoom == "classic" else
                "on the crossing" if zoom[1] == "crossing" else
                "zoomed" if zoom[0] is None else
                "from " + {(0, -1, 0): "the front", (1, 0, 0): "the side",
                           (0, 0, 1): "above"}.get(tuple(zoom[0]), "elsewhere"))
        img = Image.new("RGB", (3 * W, top + lab + 2 * H), "white")
        d = ImageDraw.Draw(img)
        d.text((10, 8), title, font=FT, fill=(0, 0, 0))
        d.text((10, 34), note, font=F, fill=(60, 60, 60))
        first = json.load(open("%s.%s.json" % (r, cols[0][0])))
        d.text((10, top), "the draft", font=FB, fill=(0, 0, 0))
        fs = first["face"] if isinstance(first["face"], list) else [first["face"]]
        d.text((10, top + 21), "face%s %s, %g deg" % ("s" if len(fs) > 1 else "",
                                                       ", ".join(map(str, fs)), first["angle"]),
               font=F, fill=rgb(C_FACE))
        d.text((10, top + 40), "neutral face %d" % first["neutral"], font=F, fill=rgb(C_NEUTRAL))
        d.text((10, top + 59), "translucent: where it turns to", font=F, fill=rgb(C_FACE))
        for ci, (col, _, label) in enumerate(cols):
            x = (ci + 1) * W
            res = json.load(open("%s.%s.json" % (r, col)))
            d.text((x + 10, top), label, font=FB, fill=(0, 0, 0))
            if res["kind"] == "refused":
                lines = [("refused", BLUE)]
            else:
                lines = [("%s, volume %.4f, %d faces" % (res["kind"], res["volume"], res["faces"]),
                          GREEN if res["kind"] == "valid" else RED),
                         ("boolean check: " + res["bop"],
                          GREEN if res["bop"] == "clean" else RED)]
                if not pieces:
                    lines.append(("orange: the faces the draft made", rgb(C_MADE)))
                if res.get("crossing"):
                    lines.append(("red: faces crossing each other", rgb(C_CROSS)))
            for li, (t, colr) in enumerate(lines):
                d.text((x + 10, top + 21 + li * 19), t, font=F, fill=colr)
        for ci in range(3):
            for row in (0, 1):
                v = "setup" if ci == 0 else cols[ci - 1][0]
                img.paste(Image.open(P + "/png/%s.%s.%d.png" % (name, v, row)).convert("RGB"),
                          (ci * W, top + lab + row * H))
            d.text((ci * W + 10, top + lab + H + 6), row2, font=F, fill=GREY)
        for ci in (1, 2):
            d.line([(ci * W, top), (ci * W, top + lab + 2 * H)], fill=(170, 170, 170), width=1)
        d.line([(0, top + lab + H), (3 * W, top + lab + H)], fill=(225, 225, 225), width=1)
        img.save(os.path.join(out, name + ".png"), optimize=True)
        print(name, os.path.getsize(os.path.join(out, name + ".png")))


if "CASE" in os.environ:
    compute()
elif len(sys.argv) > 1 and sys.argv[1] == "jobs":
    jobs()
elif len(sys.argv) > 1:
    compose(sys.argv[1])
