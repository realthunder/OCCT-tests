# The cases pictured in models/pictures: the suite's (run_tests.py) that a fix
# turned from failing to passing, each with the stage of the fix -- the fork
# commit just before it (STAGES) is the "before" column.
import os

try:
    import FreeCAD as App, Part
except ImportError:  # plain Python reads the tables only
    App = Part = None

MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

# stage -> (the fork commit just before the fix, the fix)
STAGES = {
    "s523": ("f723999a15", "16df68d224"),
    "s962": ("d8ba4ad7eb", "cf96757c36"),
    "s962b": ("1482f7d4e2", "b38f0d910c"),
    "s962c": ("e3a3779048", "2ac4fee0c6"),
    "s962d": ("d4f71dfae3", "2b9df66c48"),
    "s962e": ("6d61205cc1", "fb9200b0fd"),
    "s962f": ("1e6f5a464c", "3fa9420429"),
    "s962g": ("b6928966df", "98c6125b85"),
    "s962h": ("76de040ead", "692cae9e35"),
    "s523b": ("1e8eb69f6a", "efbe5c99fd"),
    "s876": ("f9d329a663", "538ce9f99a"),
    "s876b": ("fa8d202b81", "5310ff9d59"),
    "s876c": ("5310ff9d59", "c34722ef01"),
    "s876d": ("e25bcf2525", "2a623612a8"),
    "s894": ("5c81764cc5", "0ff4092766"),
    "s962i": ("b207bd4103", "9c44789bbb"),
    "s474": ("8f861e9dea", "09c8fe6c57"),
    "s962j": ("09c8fe6c57", "7a1fbeffb3"),
    "s523c": ("83ee729ead", "8704591b60"),
    "s962k": ("2382ef56c9", "fff5d20907"),
    "s962l": ("e6227d4943", "b9e95d0e71"),
    "s523d": ("0589170f82", "40ba54dcdf"),
    "s962m": ("b5ff91ba64", "63c8218a86"),
    "s474b": ("63c8218a86", "356bfb48a7"),
    "s962n": ("356bfb48a7", "29d7d4d038"),
    "s962o": ("29d7d4d038", "f7464716c0"),
    "s962r": ("f7464716c0", "74a9a42df4"),
    "s962s": ("74a9a42df4", "f8a25381c2"),
    "s962p": ("f8a25381c2", "93759f6d56"),
    "s962q": ("93759f6d56", "6c4e2bc29f"),
    "s962t": ("6c4e2bc29f", "fbff94bd8b"),
    "s962u": ("fbff94bd8b", "d62136427b"),
    "s962v": ("d62136427b", "6593a88daa"),
    "s962w": ("6593a88daa", "3f7ddd4bcc"),
    "s962x": ("3f7ddd4bcc", "904a86b6c0"),
    "s962y": ("904a86b6c0", "479cc80ecb"),
    "s962z": ("b9a309b7fb", "74c8a201e0"),
    "s962za": ("74c8a201e0", "247fc423f1"),
    "s962zb": ("247fc423f1", "faf4f72ee0"),
    "s962zc": ("5635c27fba", "3ba0c94072"),
    "s962zd": ("ce0ac05245", "726d9533c6"),
    "s962ze": ("61f18d7958", "f446ee4591"),
    "s962zf": ("3fb6fdcac3", "2ff60f1efd"),
    "s962zg": ("2ff60f1efd", "2bc692bfc4"),
    "s962zh": ("2bc692bfc4", "9d58debece"),
    "s962zi": ("9d58debece", "5052552dd6"),
    "s962zj": ("5052552dd6", "6505747185"),
    "s309": ("6505747185", "9c45825ba1"),
    "s309b": ("9c45825ba1", "358d611f3f"),
    "s474c": ("358d611f3f", "afb7f305d0"),
    "sarm": ("afb7f305d0", "2ec760a1d3"),
    "srib": ("2ec760a1d3", "52a5c89410"),
    "s962zk": ("e79f700798", "0669daa0b6"),
    "s962zl": ("5b5471ad11", "9735ff8875"),
    "s523e": ("61f59f6842", "1a971d66bc"),
    "sboss": ("af24dcdca0", "b234546fbe"),
    "schamfer": ("4124325682", "a2f5c2a5d4"),
    "sdraftboss": ("cc0ca7b66a", "1d642bfaaf"),
    "sthin": ("367e41af85", "b4f2f7592c"),
    "shalves": ("35f297a6d0", "892a10b753"),
    "sseam": ("20b6442003", "e549e29656"),
    "srunon": ("d1b6f7a0c2", "95a3e143e1"),
    "sfold": ("f0a499fa6d", "31cf3ce134"),
    "soff": ("2b8b6e4446", "efd99a29b5"),
    "sflat": ("0b618067bb", "cd24623b20"),
    "shandle": ("cd24623b20", "6fd966afde"),
    "ssliver": ("6fd966afde", "5fe644b95d"),
}
# stage -> the toolkits its "before" library is built of, when not TKFillet alone
STAGE_TOOLKITS = {
    "s962d": "TKFillet TKGeomAlgo",
}
# Upstream: the toolkit's files that differ from the fork, at 91be8c4c71 (an
# upstream commit 60 before 8.0.1, b8f597c677, which the branch stands on) --
# TKFillet's all, and of the other toolkits only the files a fix of these
# changed (the fork's TKGeomAlgo differs from upstream's in more than that).
UPSTREAM = "91be8c4c71"
UPSTREAM_TOOLKITS = ["TKFillet", "TKGeomAlgo"]
UPSTREAM_EXTRA = ["src/ModelingAlgorithms/TKGeomAlgo/GeomPlate/GeomPlate_BuildPlateSurface.cxx"]


def _brep(name):
    def make():
        s = Part.Shape()
        s.read(os.path.join(MODELS, name))
        return s
    return make


def _slot_wall():
    # run_tests.py's slotted block, its slot's wall split 0.7 from the outer face
    V = App.Vector
    s = Part.makeBox(10, 10, 14).cut(Part.makeBox(12, 3, 10, V(-1, 3, 5)))
    return s.generalFuse([Part.LineSegment(V(9.3, 3, 5), V(9.3, 3, 20)).toShape()])[0].Solids[0]


def _slot_outer():
    # run_tests.py's slotted block, its outer face split along y=3 below the slot's floor
    V = App.Vector
    s = Part.makeBox(10, 10, 14).cut(Part.makeBox(12, 3, 10, V(-1, 3, 5)))
    return s.generalFuse([Part.LineSegment(V(10, 3, 0), V(10, 3, 5)).toShape()])[0].Solids[0]


def _fin():
    # run_tests.py's fin padded flush with the block's side
    V = App.Vector
    return Part.makeBox(10, 10, 5).fuse(Part.makeBox(10, 3, 9, V(0, 0, 5)))


def _fin_wall():
    # the fin, its wall split 0.7 from the outer face as the slot's
    V = App.Vector
    return _fin().generalFuse([Part.LineSegment(V(9.3, 3, 5), V(9.3, 3, 20)).toShape()])[0].Solids[0]


def _arm_on_tall_block(split=True, near=False):
    # run_tests.py's arm fused to a block that goes on above it, the block's
    # side y=27.2 two faces split at the arm's top (or one face); near: its
    # side y=10.2 split there
    V = App.Vector
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 6))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    s = Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 23.75)).fuse(arm)
    cuts = []
    if split:
        cuts.append(Part.LineSegment(V(38.5, 27.2, -3.75), V(50, 27.2, -3.75)).toShape())
    if near:
        cuts.append(Part.LineSegment(V(38.5, 10.2, -3.75), V(50, 10.2, -3.75)).toShape())
    if not cuts:
        return s
    return s.generalFuse(cuts)[0].Solids[0]


def _arm_tilted_under_block(normal=(0.06, -0.06, 1)):
    # run_tests.py's: the arm on the tall block, its top a plane of the given
    # normal through the corner (38.5, 27.2, -3.75)
    V = App.Vector
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 12))
    n = V(*normal).normalize()
    plane = Part.makePlane(400, 400, V(-200, -200, 0))
    plane.Placement = App.Placement(V(38.5, 27.2, -3.75), App.Rotation(V(0, 0, 1), n))
    arm = arm.common(plane.extrude(n * -40))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    return Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 23.75)).fuse(arm)


def _arch_on_plate(split=False, R=10.0):
    # run_tests.py's arch on a plate: a half cylinder on a plate as long as
    # its diameter, the plate's ends tangent to it (and split under the
    # arch's end face)
    V = App.Vector
    plate = Part.makeBox(12, 2 * R, 2, V(-10, -R, -2))
    cyl = Part.makeCylinder(R, 2, V(0, 0, 0), V(1, 0, 0)).common(
        Part.makeBox(2, 2 * R, R, V(0, -R, 0)))
    s = plate.fuse(cyl).removeSplitter()
    if split:
        s = s.generalFuse([Part.LineSegment(V(0, y, -2), V(0, y, 0)).toShape()
                           for y in (-R, R)])[0].Solids[0]
    return s


def _arm_on_block():
    # run_tests.py's arm fused to a block, the seam of their bottoms from y=27.2 to 10.2
    V = App.Vector
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 6))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    return Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 6)).fuse(arm)


def _post_on_plate(draft=0.0, turn=90):
    # run_tests.py's post on a plate: a cylinder r3 on a stadium plate whose side y=-3 runs
    # tangent into the plate's round end under the post, or a cone drafted <draft> deg.
    # The post turned a quarter, its seam at the back: the pictures mark a seam's edge red.
    # Turned three quarters, the seam runs up from the fillet's end.
    import math
    V = App.Vector
    plate = Part.makeCylinder(3, 3).fuse(Part.makeBox(12, 6, 3, V(-12, -3, 0))).removeSplitter()
    if draft:
        post = Part.makeCone(3, 3 - 15 * math.tan(math.radians(draft)), 15, V(0, 0, 3))
    else:
        post = Part.makeCylinder(3, 15, V(0, 0, 3))
    post.rotate(V(0, 0, 0), V(0, 0, 1), turn)
    return plate.fuse(post)


def _teardrop_post_on_plate():
    # run_tests.py's teardrop post: drafted 1 deg, its base the plate's round end's
    # circle over 41 deg of the plate's top, then a straight wall tangent to it
    import math
    V = App.Vector
    t1 = -math.pi / 2 - math.radians(41.0)
    q0 = V(3 * math.cos(t1), 3 * math.sin(t1), 0) + V(math.sin(t1), -math.cos(t1), 0) * 6
    g = math.acos(3 / math.hypot(q0.x, q0.y))
    t2 = math.atan2(q0.y, q0.x) + g
    if abs(math.cos(t2 - t1) - 1) < 1e-9:
        t2 -= 2 * g
    while t2 < t1:
        t2 += 2 * math.pi
    tan = math.tan(math.radians(1.0))

    def section(z):
        rad = 3 - (z - 3) * tan
        n1, n2 = V(math.cos(t1), math.sin(t1), 0), V(math.cos(t2), math.sin(t2), 0)
        det = n1.x * n2.y - n1.y * n2.x
        q = V(rad * (n2.y - n1.y) / det, rad * (n1.x - n2.x) / det, z)
        return rad, V(rad * math.cos(t1), rad * math.sin(t1), z), \
            V(rad * math.cos(t2), rad * math.sin(t2), z), q

    def cap(z, rad, a, b, q):
        tm = (t1 + t2) / 2
        arc = Part.Arc(a, V(rad * math.cos(tm), rad * math.sin(tm), z), b).toShape()
        return Part.Face(Part.Wire([arc, Part.makeLine(b, q), Part.makeLine(q, a)]))

    r0, a0, b0, q0_ = section(3)
    r1, a1, b1, q1_ = section(18)
    cone = Part.Cone(V(0, 0, 3), V(0, 0, 18), r0, r1)
    faces = [cone.toShape(t1 + 2 * math.pi, t2 + 2 * math.pi, 0, 15 / math.cos(math.radians(1.0))),
             Part.Face(Part.makePolygon([a0, q0_, q1_, a1, a0])),
             Part.Face(Part.makePolygon([q0_, b0, b1, q1_, q0_])),
             cap(3, r0, a0, b0, q0_), cap(18, r1, a1, b1, q1_)]
    shell = Part.Shell(faces)
    shell.sewShape()
    post = Part.Solid(shell)
    if post.Volume < 0:
        post.reverse()
    plate = Part.makeCylinder(3, 3).fuse(Part.makeBox(12, 6, 3, V(-12, -3, 0))).removeSplitter()
    return plate.fuse(post).removeSplitter()


def _slant_block():
    """run_tests.py's slant_block: a 12x3 prism whose top slopes down past
    x=4, its front wall (y=0) split at x=5."""
    V = App.Vector
    prof = Part.Face(Part.makePolygon([V(0, 0, 0), V(12, 0, 0), V(12, 0, 6), V(4, 0, 10),
                                       V(0, 0, 10), V(0, 0, 0)]))
    s = prof.extrude(V(0, 3, 0))
    return s.generalFuse([Part.LineSegment(V(5, 0, 0), V(5, 0, 9.5)).toShape()])[0].Solids[0]


def _rib_foot():
    """run_tests.py's rib_foot: a block and on it a rib whose underside
    slopes 45 deg out from the block's edge, its front wall split at x=1."""
    V = App.Vector
    blk = Part.makeBox(10, 6, 4, V(0, 0, -4))
    prof = Part.Face(Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 0, 8), V(-3, 0, 8),
                                       V(-3, 0, 3), V(0, 0, 0)]))
    s = blk.fuse(prof.extrude(V(0, 3, 0))).removeSplitter()
    return s.generalFuse([Part.LineSegment(V(1, 3, 0), V(1, 3, 8)).toShape()])[0].Solids[0]


def _ledge():
    """run_tests.py's ledge: a base whose outline turns at (6,3) and on it a
    block, the block's side y=3 and the base's below it one plane in two."""
    V = App.Vector
    base = Part.Face(Part.makePolygon([V(0, 10, -4), V(0, 0, -4), V(6, 3, -4), V(10, 3, -4),
                                       V(10, 10, -4), V(0, 10, -4)])).extrude(V(0, 0, 4))
    return base.fuse(Part.makeBox(4, 7, 5, V(6, 3, 0)))


def _pocket_by_split():
    """run_tests.py's pocket_by_split: a box whose front is split at x=5, a
    pocket in it 0.3 from the split."""
    V = App.Vector
    s = Part.makeBox(10, 6, 10)
    s = s.generalFuse([Part.LineSegment(V(5, 0, 0), V(5, 0, 10)).toShape()])[0].Solids[0]
    return s.cut(Part.makeBox(2.7, 2, 4, V(5.3, 0, 3)))


def _strip_box():
    """run_tests.py's strip_box: a box whose bottom and end faces are split
    2 from the side x=0."""
    V = App.Vector
    cuts = [Part.LineSegment(V(2, 0, 0), V(2, 10, 0)).toShape(),
            Part.LineSegment(V(2, 0, 0), V(2, 0, 4)).toShape(),
            Part.LineSegment(V(2, 10, 0), V(2, 10, 4)).toShape()]
    return Part.makeBox(10, 10, 4).generalFuse(cuts)[0].Solids[0]


def _slot_both():
    # run_tests.py's slotted block, its slot's wall and its outer face both split
    V = App.Vector
    s = _slot_outer()
    return s.generalFuse([Part.LineSegment(V(9.3, 3, 5), V(9.3, 3, 20)).toShape()])[0].Solids[0]


def _slot_by_slope():
    """run_tests.py's slot_by_slope: a block and on it two walls with a slot
    between them, overhanging the block's side x=0 by a 45 deg slope; the
    slot's wall y=4 split 0.7 from that side."""
    V = App.Vector
    s = Part.makeBox(10, 10, 5)
    side = Part.Face(Part.makePolygon([V(0, 0, 5), V(10, 0, 5), V(10, 0, 10), V(-5, 0, 10),
                                       V(0, 0, 5)]))
    for y, d in ((0, 4), (7, 3)):
        p = side.copy()
        p.translate(V(0, y, 0))
        s = s.fuse(p.extrude(V(0, d, 0)))
    s = s.removeSplitter()
    return s.generalFuse([Part.LineSegment(V(0.7, 4, 5), V(0.7, 4, 10)).toShape()])[0].Solids[0]


def _boss_flush():
    """run_tests.py's _boss(5): a cylinder boss r5 on a 30x20x3 plate, flush
    with the plate's side y=0."""
    V = App.Vector
    return Part.makeBox(30, 20, 3).fuse(Part.makeCylinder(5, 10, V(15, 5, 3))).removeSplitter()


def _boss_drafted():
    """run_tests.py's _drafted: a cone boss, radius 5 to 4 over 10, on a
    30x20x3 plate, flush with the plate's side y=0 at its foot."""
    V = App.Vector
    return Part.makeBox(30, 20, 3).fuse(Part.makeCone(5, 4, 10, V(15, 5, 3))).removeSplitter()


def _boss_halves():
    """run_tests.py's _boss(5, 90.0): the flush boss turned a quarter, its
    seam at (15,10) opposite the tangent point (15,0): the foot in two equal
    halves."""
    V = App.Vector
    b = Part.makeCylinder(5, 10, V(0, 0, 3))
    b.rotate(V(0, 0, 0), V(0, 0, 1), 90.0)
    b.translate(V(15, 5, 0))
    return Part.makeBox(30, 20, 3).fuse(b).removeSplitter()


def _boss_seam():
    """run_tests.py's _boss(5, 270.0): the flush boss turned three quarters,
    its seam up from the tangent point (15,0): the foot one closed edge."""
    V = App.Vector
    b = Part.makeCylinder(5, 10, V(0, 0, 3))
    b.rotate(V(0, 0, 0), V(0, 0, 1), 270.0)
    b.translate(V(15, 5, 0))
    return Part.makeBox(30, 20, 3).fuse(b).removeSplitter()


def _pocket_mouth():
    """run_tests.py's pocket_mouth: a block with a round pocket that widens
    below a step and a slot out of it, the slot's wall split above the step
    1.25 from the pocket and the block's top by a circle from the same
    foot."""
    V = App.Vector
    seam = lambda c: c.rotated(V(0, 0, 0), V(0, 0, 1), 5.5)
    s = Part.makeBox(50, 50, 10, V(-25, -25, 0))
    s = s.cut(seam(Part.makeCylinder(15.5, 5, V(0, 0, 5))))
    s = s.cut(seam(Part.makeCylinder(16.75, 3, V(0, 0, 2))))
    s = s.cut(Part.makeBox(19.75, 3, 8, V(0, 0, 2))).removeSplitter()
    return s.generalFuse([Part.LineSegment(V(16.75, 0, 5), V(16.75, 0, 10)).toShape(),
                          seam(Part.makeCircle(16.75, V(0, 0, 10)))])[0].Solids[0]


def _chamfer_corner(box=False):
    """run_tests.py's chamfer_corner: a 40x30x10 block -- makeBox, or a
    polygon extruded, its faces' edges the other way round -- with fillet 2
    on the edges at y=30 (the two verticals, the top one) and on
    (0,30,0)-(0,0,0)."""
    V = App.Vector
    b = (Part.makeBox(40, 30, 10) if box else Part.Face(Part.makePolygon(
        [V(0, 0, 0), V(40, 0, 0), V(40, 30, 0), V(0, 30, 0), V(0, 0, 0)])).extrude(V(0, 0, 10)))
    ends = [((0, 30, 0), (0, 30, 10)), ((0, 30, 0), (0, 0, 0)), ((40, 30, 0), (40, 30, 10)),
            ((40, 30, 10), (0, 30, 10))]
    return b.makeFillet(2, [edge_between(b, a, c) for a, c in ends])


SHAPES = {
    "boxcyl": _brep("issue523_box_cylinder.brep"),
    "arch": _arch_on_plate,
    "archsplit": lambda: _arch_on_plate(split=True),
    "slotwall": _slot_wall,
    "p962": _brep("issue962_pocket002.brep"),
    "fin": _fin,
    "finwall": _fin_wall,
    "armfoot": _arm_on_block,
    "armtall": _arm_on_tall_block,
    "armwhole": lambda: _arm_on_tall_block(split=False),
    "armnear": lambda: _arm_on_tall_block(split=False, near=True),
    "armtilt": _arm_tilted_under_block,
    "p474": _brep("issue474_fillet003_base.brep"),
    "p273": _brep(os.path.join("..", "..", "draft", "sweep", "shapes", "issue273_Fillet.brep")),
    "postplate": _post_on_plate,
    "postdraft": lambda: _post_on_plate(draft=1.0),
    "postseam": lambda: _post_on_plate(turn=270),
    "postplane": _teardrop_post_on_plate,
    "p876": _brep("issue876_fillet_base.brep"),
    "slantblock": _slant_block,
    "ribfoot": _rib_foot,
    "ledge": _ledge,
    "p474b": _brep("issue474_fillet002_base.brep"),
    "pocketsplit": _pocket_by_split,
    "stripbox": _strip_box,
    "slotouter": _slot_outer,
    "slotboth": _slot_both,
    "slotslope": _slot_by_slope,
    "pocketmouth": _pocket_mouth,
    "bossflush": _boss_flush,
    "bossdrafted": _boss_drafted,
    "bosshalves": _boss_halves,
    "bossseam": _boss_seam,
    "chfcorner": _chamfer_corner,
    "chfcornerbox": lambda: _chamfer_corner(box=True),
}


def _plane_at(axis, value, lo=None, hi=None):
    """A planar face lying in <axis> = value, its bounding box's centre
    between lo and hi on the other axes (dicts axis -> bound)."""
    def pick(f):
        if f.Surface.__class__.__name__ != "Plane":
            return False
        b = f.BoundBox
        mn, mx = getattr(b, axis.upper() + "Min"), getattr(b, axis.upper() + "Max")
        if abs(mn - value) > 1e-6 or abs(mx - value) > 1e-6:
            return False
        c = b.Center
        return all(lo[a] <= getattr(c, a) for a in lo or {}) and all(
            getattr(c, a) <= hi[a] for a in hi or {})
    return pick


def _plate_near(x, y, z, reach=1.0):
    """A corner's plate: a B-spline face whose vertices all lie within <reach>
    of the corner (x, y, z). Not its bounding box: a plate that went wrong
    has its poles far out, the box with them."""
    def pick(f):
        if f.Surface.__class__.__name__ != "BSplineSurface":
            return False
        p = App.Vector(x, y, z)
        return all(v.Point.distanceToPoint(p) <= reach for v in f.Vertexes)
    return pick


def _flat_near(x, y, z, reach=1.0):
    """A flat face that closes a corner: a plane face whose vertices all lie
    within <reach> of the corner (x, y, z). Where a plate closes it there is
    none, and the row stays empty."""
    def pick(f):
        if f.Surface.__class__.__name__ != "Plane":
            return False
        c = App.Vector(x, y, z)
        return all(v.Point.distanceToPoint(c) < reach for v in f.Vertexes)
    return pick


# shape -> the face whose (u, v) outline the third row draws, found in a result
UVFACE = {
    # the corner's cylinder, not a fillet of the same radius
    "boxcyl": (lambda f: f.Surface.__class__.__name__ == "Cylinder"
               and abs(f.Surface.Radius - 2) < 1e-6 and abs(abs(f.Surface.Axis.z) - 1) < 1e-9),
    # the arch's cylinder, which grows over the fillet's ends
    "arch": (lambda f: f.Surface.__class__.__name__ == "Cylinder"
             and abs(f.Surface.Radius - 10) < 1e-6),
    "archsplit": (lambda f: f.Surface.__class__.__name__ == "Cylinder"
                  and abs(f.Surface.Radius - 10) < 1e-6),
    # the slot's floor, where the fillet ends
    "slotwall": _plane_at("z", 5),
    # the slot's floor at e101's foot (y 13.7..17.1); for e50 see UVFACE_CASE
    "p962": _plane_at("z", 14, {"y": 13.0}, {"y": 17.1}),
    # the fin's outer face, which the fillet's line runs on
    "fin": _plane_at("x", 10, {"z": 5.0 + 1e-6}),
    # the block's top beside the fin, where the fillet ends
    "finwall": _plane_at("z", 5),
    # the arm's bottom, which holds the seam at x=38.5
    "armfoot": _plane_at("z", -9.75, None, {"x": 38.5}),
    # the corner's plate at the edge's top
    "armtall": (lambda f: f.Surface.__class__.__name__ == "BSplineSurface"
                and f.BoundBox.isInside(App.Vector(38.5, 27.2, -3.76))),
    # the arm's top, which the fillet's end cuts
    "armwhole": _plane_at("z", -3.75),
    # the arm's top, which grows over the fillet's end
    "armnear": _plane_at("z", -3.75),
    # the flat face under the block's wall, in the plane of the arm's top
    "armtilt": _flat_near(38.5, 27.2, -3.75),
    # the corner's plate at edge 6's top
    "p474": _plate_near(-13, 0, 13),
    # the patch at the pocket's apex
    "p273": _plate_near(0, 15.0135, 30.6, 1.5),
    # the plate's side, whose outline ran up to the top and back down
    "postplate": _plane_at("y", -3),
    # the post's cone, carried on below its base by the cut
    "postdraft": lambda f: f.Surface.__class__.__name__ == "Cone",
    # the post's cylinder, whose wire jumped a period at the seam
    "postseam": (lambda f: f.Surface.__class__.__name__ == "Cylinder"
                 and f.BoundBox.ZMax > 10),
    # the post's wall the cone runs on into, which the cut now crosses
    "postplane": (lambda f: f.Surface.__class__.__name__ == "Plane"
                  and abs(f.Surface.Axis.z) < 0.5 and f.BoundBox.ZMax > 10
                  and f.BoundBox.YMin < -2.0),
    # the set back corner's plate at (17, 16.75, 3)
    "p876": _plate_near(17, 16.75, 3, reach=1.5),
    # the wall's second piece, which the fillet's line now crosses onto
    "slantblock": _plane_at("y", 0, {"x": 5.5}),
    # the block's top, which the fillet's end now grows into under the rib
    "ribfoot": _plane_at("z", 0),
    # the base's side under the block's (y=3, below the top), whose wire crossed itself
    "ledge": _plane_at("y", 3, None, {"z": -1.0}),
    # the ramp's face that reaches down to z=11.1, one of the two meeting in the long edge
    "p474b": (lambda f: f.Surface.__class__.__name__ == "BSplineSurface"
              and f.BoundBox.ZMin < 12.0 and f.BoundBox.ZMax > 17.5),
    # the front's far piece (x 0..5), which the fillet's line lies on
    "pocketsplit": _plane_at("y", 0, None, {"x": 4.0}),
    # the end face's near piece (y=0, x 0..2), which the corner cuts
    "stripbox": _plane_at("y", 0, None, {"x": 1.9}),
    # the outer face's piece below the slot's wall (x=10, y 0..3), which the corner's edge is on
    "slotouter": _plane_at("x", 10, None, {"y": 2.99}),
    # the slot's wall, its piece at the mouth (y=3, x 9.3..10), which the cut grows downward
    "slotboth": _plane_at("y", 3, {"x": 9.4}),
    # the slot's wall, its piece at the block's side (y=4, x -5..0.7), which the cut grows downward
    "slotslope": _plane_at("y", 4, None, {"x": 0.0}),
    # the slot's wall, its piece beyond the split (x from 16.75)
    "pocketmouth": _plane_at("y", 0, {"x": 17.0}),
    # the plate's side the boss is flush with, which grows a peak over the gap
    "bossflush": _plane_at("y", 0),
    # the same side, which grows a bump under the gap between the fillet's ends
    "bossdrafted": _plane_at("y", 0),
    # the same side
    "bosshalves": _plane_at("y", 0),
    "bossseam": _plane_at("y", 0),
    # the back face, both fillets flush with it at the corner, whose corner the cut takes off
    "chfcorner": _plane_at("y", 30),
    "chfcornerbox": _plane_at("y", 30),
}
# case -> a third-row face other than its shape's
UVFACE_CASE = {
    # the plate's side under the post's long wall, the thin fillet along its top
    "issue876_kink_e52_r0.3": _plane_at("y", -16.75),
    # the fin's wall, its far piece (x 0..9.3), where the two fillets' lines meet
    "fin_on_block_wall_piece_foot_and_upright_r1": _plane_at("y", 3, None, {"x": 5.0}),
    # the flat face under the block's wall, in the plane of the arm's top
    "issue962_e36_r2": _flat_near(38.5, 27.2, -3.75),
    "arm_on_tall_block_whole_r0.8": _flat_near(38.5, 27.2, -3.75),
    # the pocket's radial wall at edge 14, its piece beyond the split (r from 16.75)
    "issue962_pocket_edge_r2": (lambda f: f.Surface.__class__.__name__ == "Plane"
                                and abs(f.Surface.Axis.z) < 1e-6
                                and f.BoundBox.Center.distanceToPoint(
                                    App.Vector(-12.7, -13.3, -6.75)) < 1.0),
    # the slot's wall, its piece at the mouth, as on the block split twice
    "slot_split_wall_mouth_r0.8": _plane_at("y", 3, {"x": 9.4}),
    # the block's side (y=10.2), its piece past the rib's, from x=38.5 on
    "issue962_e72_r0.8": _plane_at("y", 10.2, {"x": 40.0, "z": 5.0}, {"x": 50.0}),
    # the slot's wall, its piece at the mouth
    "slot_split_wall_top_and_upright_r1": _plane_at("y", 3, {"x": 9.4}),
    # the rib's wall (y=10.2) under the top's edge, its piece up to x=38.5
    "issue962_rib_top_corner_r1": _plane_at("y", 10.2, {"z": 20.0}, {"x": 38.4}),
    # the rib's wall (y=13.7), its piece at the floor's corner, up to x=38.96
    "issue962_e52_r0.8": _plane_at("y", 13.7, None, {"x": 38.0}),
    # the arm's top (z=-3.75), which grows over the fillet's end
    "issue962_block_far_edge_over_arm_r2": _plane_at("z", -3.75, None, {"x": 38.6}),
    # the arm's top, the piece of the top beyond the split
    "arm_on_block_far_z-3.75_upright_and_block_r1": _plane_at("z", -3.75, None, {"x": 38.5}),
    # the rib's wall (y=13.7), its second piece, from x=38.96 on
    "issue962_rib_top_near_r1": _plane_at("y", 13.7, {"x": 39.0}, {"x": 50.0}),
    # the fin's outer face, as on the fin whose wall is one face
    "fin_on_block_wall_top_and_upright_r1": _plane_at("x", 10, {"z": 5.0 + 1e-6}),
    # the rib's wall (y=20.3), its second piece, from x=39.197 on
    "issue962_rib_top_r0.8": _plane_at("y", 20.3, {"x": 40.0}, {"x": 50.0}),
    # the B-spline face at edge 51's foot, which the corner extends
    "issue474_f003_e51_r0.8": (lambda f: f.Surface.__class__.__name__ == "BSplineSurface"
                               and f.BoundBox.ZMin < 28.3 and f.BoundBox.ZMax < 29.8
                               and f.BoundBox.isInside(App.Vector(6.0, 10.6, 29.0))),
    # the block's top at the rib's foot (y 20.3..23.7, now from 18.8)
    "issue962_rib_foot_r1.5": _plane_at("z", 14, {"x": 38.0, "y": 19.0}, {"y": 24.0}),
    # the wall y=10.2 beside e50, its piece from x=38.5 on (the hexagon's)
    "issue962_e50_r0.8": _plane_at("y", 10.2, {"x": 40.0}, {"x": 50.0}),
    # the arm's bottom, which holds the seam at x=38.5
    "issue962_fillet_r0.8": _plane_at("z", -9.75, None, {"x": 38.5}),
    # the corner's plate at edge 36's top
    "issue962_e36_r0.3": (lambda f: f.Surface.__class__.__name__ == "BSplineSurface"
                          and f.BoundBox.isInside(App.Vector(38.5, 27.2, -3.76))),
    # the corner's plate at edge 56's foot
    "issue962_e56_r0.8": _plate_near(38.5, 27.2, -3.75),
    # the corner's plate at edge 33's end
    "issue962_e33_r0.3": _plate_near(38.5, 10.2, -3.75),
    # the block's top beside the slot (y 0..3), where the fillet ends at the top
    "slot_split_wall_r0.7001": _plane_at("z", 14, None, {"y": 3.0}),
    # the set back corner's plate where the fillet's end was refused
    "seam_end_top_r2.5": _plate_near(2, 0, 10, reach=7.0),
    "seam_end_top_r3": _plate_near(2, 0, 10, reach=8.0),
    # the block's top at the rib's foot, as at 1.5
    "issue962_rib_foot_r0.9865": _plane_at("z", 14, {"x": 38.0, "y": 19.0}, {"y": 24.0}),
    # the top: the whole of it before, the box's rectangle after (the disc
    # its own face)
    "pinch_top_r2": _plane_at("z", 10, {"x": 3.0}),
    # the bottom: the whole of it before, the box's rectangle after (the disc
    # its own face)
    "issue523_bottom_rim_and_edge_a_r1": _plane_at("z", 0, {"x": 3.0}),
    # the block's side y=10.2 below the arm's top (z -9.75..-3.75)
    "issue962_top_wall_r0.8": _plane_at("y", 10.2, {"x": 40.0}, {"z": -5.0}),
    # the same side's piece beside the pocket, the rib's (x 34.5..38.5, z from 14)
    "issue962_hex_mouth_r0.8": _plane_at("y", 10.2, {"z": 15.0}, {"x": 38.4}),
    # the block's top (z=-3.75, x from 38.5), which the corner's edge starts on
    "arm_on_block_z-3.75_upright_and_block_r1": _plane_at("z", -3.75, {"x": 40.0}),
    # the side's piece beside the pocket's again, which the mouth's fillet has its line on
    "issue962_hex_mouth_top_mouth_and_side_r0.3": _plane_at("y", 10.2, {"z": 15.0}, {"x": 38.4}),
    "issue962_hex_mouth_top_all_three_r1": _plane_at("y", 10.2, {"z": 15.0}, {"x": 38.4}),
    # the side's piece the pocket is in (x from 38.5, z -3.75..32.25)
    "issue962_hex_mouth_top_side_and_inner_r1": _plane_at("y", 10.2, {"x": 40.0, "z": 5.0}),
    "issue962_hex_mouth_top_side_r1": _plane_at("y", 10.2, {"x": 40.0, "z": 5.0}),
    # the first edge's fillet, a cylinder along (-0.242, 0.970, 0), which the second cuts
    "arm_on_block_far_top_edges_r1": (lambda f: f.Surface.__class__.__name__ == "Cylinder"
                                      and abs(abs(f.Surface.Axis.y) - 0.970) < 0.01),
}
NAMES = {
    "boxcyl": "10 box with a 3/4 cylinder r2 at a corner (#523, Part Connect)",
    "arch": "a half cylinder r10, 2 thick, on a 12x20x2 plate whose ends are tangent to it",
    "archsplit": "the arch on its plate, the plate's ends split under the arch's end face",
    "slotwall": "10x10x14 block, a slot down to z=5, the slot's wall two faces split 0.7 "
                "from the outer face",
    "p962": "#962's Pocket002, the Fillet's input (a PartDesign body without Refine)",
    "fin": "10x10x5 block with a 10x3x9 fin padded flush with its side x=10",
    "finwall": "the fin flush with the block, its wall two faces split 0.7 from the outer face",
    "armfoot": "an arm fused to an 11.5x17x6 block, their bottoms two faces split along x=38.5",
    "armtall": "the arm fused to an 11.5x17x23.75 block, the block's side y=27.2 two faces "
               "split at the arm's top",
    "armwhole": "the arm fused to an 11.5x17x23.75 block, the block's side y=27.2 one face",
    "armnear": "the arm fused to an 11.5x17x23.75 block, the block's side y=10.2 two faces "
               "split at the arm's top",
    "armtilt": "the arm fused to an 11.5x17x23.75 block, the arm's top tilted 4.9 deg about "
               "the corner under the block's wall, the block's side y=27.2 one face",
    "p474": "#474's Fillet003 input (a PartDesign body)",
    "p273": "#273's Fillet input (a PartDesign body: a cup, a handle with a pocket in its top)",
    "postplate": "a post r3 on a 3-thick plate, the plate's side y=-3 running tangent into "
                 "its round end under the post",
    "postdraft": "the post on the plate drafted 1 deg, a cone on the round end's cylinder",
    "postseam": "the post on the plate turned so that its seam runs up from the edge's end",
    "postplane": "the drafted post with a straight wall tangent to its cone 41 deg round "
                 "from the edge's end",
    "p876": "#876's first Fillet input (a PartDesign body, its walls drafted 1 deg)",
    "slantblock": "a 12x3x10 prism, its top sloping down past x=4, its front wall two faces "
                  "split at x=5",
    "ribfoot": "a 10x6x4 block and on it a 3-thick rib whose underside slopes 45 deg out "
               "from the block's edge, the rib's front wall two faces split at x=1",
    "ledge": "a 4-thick base whose outline turns at (6,3) and on it a 4x7x5 block, the "
             "block's side y=3 and the base's below it one plane in two faces",
    "p474b": "#474's Fillet002 input (a PartDesign body, a helical ramp round a hub)",
    "pocketsplit": "a 10x6x10 box, its front two faces split at x=5, with a pocket in it "
                   "0.3 from the split",
    "stripbox": "a 10x10x4 box, its bottom and its end faces split 2 from the side x=0",
    "slotouter": "10x10x14 block, a slot down to z=5, the outer face x=10 two faces split "
                 "along y=3 below the slot's floor",
    "slotboth": "10x10x14 block, a slot down to z=5, its wall split 0.7 from the outer face "
                "and the outer face split along y=3 below the floor",
    "slotslope": "10x10x5 block, on it two walls and a slot between, the walls overhanging "
                 "the side x=0 by a 45 deg slope; the slot's wall y=4 split 0.7 from the side",
    "pocketmouth": "a block with a round pocket r15.5 that widens to r16.75 below z=5 and a "
                   "slot out of it; the slot's wall split 1.25 from the pocket, the top by the "
                   "circle r16.75",
    "bossflush": "a cylinder boss r5 on a 30x20x3 plate, flush with the plate's side y=0",
    "bossdrafted": "a cone boss, r5 to 4, on a 30x20x3 plate, flush at its foot with the "
                   "plate's side y=0",
    "bosshalves": "a cylinder boss r5 on a 30x20x3 plate, flush with the plate's side y=0, "
                  "turned a quarter: its seam at (15,10), opposite the tangent point",
    "bossseam": "a cylinder boss r5 on a 30x20x3 plate, flush with the plate's side y=0, "
                "turned three quarters: its seam up from the tangent point (15,0)",
    "chfcorner": "a 40x30x10 block (a polygon extruded), fillet 2 on its edges at y=30 and "
                 "on (0,30,0)-(0,0,0)",
    "chfcornerbox": "a 40x30x10 block (makeBox), fillet 2 on its edges at y=30 and on "
                    "(0,30,0)-(0,0,0)",
}
# shape -> the whole shape's view: (center, height)
VIEW = {
    "boxcyl": ((4, 4, 5), 19.0),  # the box and cylinder span -2..10 on each axis
    "arch": ((-4, 0, 3), 30.0),
    "archsplit": ((-4, 0, 3), 30.0),
    "slotwall": ((5, 5, 7), 20.0),
    "p962": ((16, 4, 11), 62.0),
    "fin": ((5, 5, 7), 20.0),
    "finwall": ((5, 5, 7), 20.0),
    "armfoot": ((30, 9, -6.75), 42.0),
    "armtall": ((30, 9, 2), 46.0),
    "armwhole": ((30, 9, 2), 46.0),
    "armnear": ((30, 9, 2), 46.0),
    "armtilt": ((30, 9, 2), 46.0),
    "p474": ((-1.4, 0, 24.3), 34.0),
    "p273": ((0, 2, 16), 44.0),
    "postplate": ((-4.5, 0, 9), 20.0),
    "postdraft": ((-4.5, 0, 9), 20.0),
    "postseam": ((-4.5, 0, 9), 20.0),
    "postplane": ((-4.5, 0, 9), 20.0),
    "p876": ((0, 0, 10), 46.0),
    "slantblock": ((6, 1.5, 5), 14.0),
    "ribfoot": ((3.5, 3, 2), 16.0),
    "ledge": ((5, 5, 0.5), 16.0),
    "p474b": ((0, 0, 9), 34.0),
    "pocketsplit": ((5, 3, 5), 17.0),
    "stripbox": ((5, 5, 2), 17.0),
    "slotouter": ((5, 5, 7), 20.0),
    "slotboth": ((5, 5, 7), 20.0),
    "slotslope": ((3, 5, 5), 20.0),
    "pocketmouth": ((14, 0, 6), 24.0),
    "bossflush": ((15, 10, 5), 24.0),
    "bossdrafted": ((15, 10, 5), 24.0),
    "bosshalves": ((15, 10, 5), 24.0),
    "bossseam": ((15, 10, 5), 24.0),
    "chfcorner": ((20, 15, 5), 40.0),
    "chfcornerbox": ((20, 15, 5), 40.0),
}
# shape -> (what the third row's face is, whether to draw u gridlines at pi/2)
UVLABEL = {
    "boxcyl": ("the cylinder face", True),
    "arch": ("the arch's cylinder", False),
    "archsplit": ("the arch's cylinder", False),
    "slotwall": ("the slot's floor", False),
    "p962": ("the face at the fillet's end", False),
    "fin": ("the fin's outer face", False),
    "finwall": ("the block's top", False),
    "armfoot": ("the arm's bottom", False),
    "armtall": ("the corner's plate", False),
    "armwhole": ("the arm's top", False),
    "armnear": ("the arm's top", False),
    "armtilt": ("the flat face under the wall", False),
    "p474": ("the corner's plate", False),
    "p273": ("the face at the apex", False),
    "postplate": ("the plate's side", False),
    "postdraft": ("the post's cone", False),
    "postseam": ("the post's cylinder", True),
    "postplane": ("the post's wall beyond the cone", False),
    "p876": ("the corner's plate", False),
    "slantblock": ("the wall's second piece", False),
    "ribfoot": ("the block's top", False),
    "ledge": ("the base's side below the block's", False),
    "p474b": ("the ramp's face beside the long edge", False),
    "pocketsplit": ("the front's far piece", False),
    "stripbox": ("the end face's near piece", False),
    "slotouter": ("the outer face's piece below the wall", False),
    "slotboth": ("the slot's wall, its piece at the mouth", False),
    "slotslope": ("the wall's piece at the block's side", False),
    "pocketmouth": ("the slot's wall beyond the split", False),
    "bossflush": ("the plate's side", False),
    "bossdrafted": ("the plate's side", False),
    "bosshalves": ("the plate's side", False),
    "bossseam": ("the plate's side", False),
    "chfcorner": ("the back face y=30", False),
    "chfcornerbox": ("the back face y=30", False),
}
# case -> the same, when its face is not the shape's (UVFACE_CASE)
UVLABEL_CASE = {
    "issue876_kink_e52_r0.3": ("the plate's side under the long wall", False),
    "fin_on_block_wall_piece_foot_and_upright_r1": ("the fin's wall, its far piece", False),
    "issue962_mouth_y17.1_floor_and_upright_r1.5": ("the slot's floor", False),
    "issue962_e36_r2": ("the flat face under the wall", False),
    "arm_on_tall_block_whole_r0.8": ("the flat face under the wall", False),
    "issue962_pocket_edge_r2": ("the slot's wall beyond the split", False),
    "slot_split_wall_mouth_r0.8": ("the slot's wall, its piece at the mouth", False),
    "issue962_e72_r0.8": ("the block's side past the rib's piece", False),
    "issue962_e52_r0.8": ("the rib's wall, its piece at the floor", False),
    "slot_split_wall_top_and_upright_r1": ("the slot's wall, its piece at the mouth", False),
    "issue962_rib_top_corner_r1": ("the rib's wall under the top's edge", False),
    "issue962_rib_top_r0.8": ("the rib's wall, its second piece", False),
    "fin_on_block_wall_top_and_upright_r1": ("the fin's outer face", False),
    "issue962_block_far_edge_over_arm_r2": ("the arm's top", False),
    "arm_on_block_far_z-3.75_upright_and_block_r1": ("the arm's top", False),
    "issue962_rib_top_near_r1": ("the rib's wall, its second piece", False),
    "issue962_rib_foot_r1.5": ("the block's top at the rib's foot", False),
    "issue474_f003_e51_r0.8": ("the face at the fillet's end", False),
    "slot_split_wall_r0.7001": ("the block's top beside the slot", False),
    "seam_end_top_r2.5": ("the corner's plate", False),
    "seam_end_top_r3": ("the corner's plate", False),
    "issue962_rib_foot_r0.9865": ("the block's top at the rib's foot", False),
    "pinch_top_r2": ("the top, the box's part", False),
    "issue523_bottom_rim_and_edge_a_r1": ("the bottom, the box's part", False),
    "issue962_top_wall_r0.8": ("the block's side below the arm's top", False),
    "issue962_hex_mouth_r0.8": ("the side's piece beside the pocket's", False),
    "arm_on_block_z-3.75_upright_and_block_r1": ("the block's top", False),
    "arm_on_block_far_top_edges_r1": ("the first edge's fillet", True),
    "issue962_hex_mouth_top_mouth_and_side_r0.3": ("the side's piece beside the pocket's", False),
    "issue962_hex_mouth_top_all_three_r1": ("the side's piece beside the pocket's", False),
    "issue962_hex_mouth_top_side_and_inner_r1": ("the side's piece the pocket is in", False),
    "issue962_hex_mouth_top_side_r1": ("the side's piece the pocket is in", False),
}
_FOOT = [((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)), ((38.5, 10.2, -3.75), (38.5, 10.2, -9.75))]
_FILLET962 = [((50, 10.2, -3.75), (50, 10.2, 22)), ((50, 13.7, 22), (50, 13.7, 14)),
              ((50, 17.1, 14), (50, 17.1, 22)), ((50, 20.3, 22), (50, 20.3, 14)),
              ((50, 23.7, 14), (50, 23.7, 22)), ((50, 27.2, -3.75), (50, 27.2, 22)),
              ((38.5, 27.2, -3.75), (38.5, 27.2, 14)), ((38.5, 10.2, -3.75), (38.5, 10.2, 14))] + _FOOT + [
              ((10.898402, 16.470802, -3.75), (10.898402, 16.470802, -9.75)),
              ((17.356038, -9.42499, -3.75), (17.356038, -9.42499, -9.75))]
# name -> (stage, shape, the edge by its ends -- or a list of them --, radius, expected volume,
#          the point to zoom on, the direction the camera looks from)
# the top corner of the hexagonal pocket's mouth
_HEXV = ((38.8, 10.2, 24.4248711),)
_HALVES_FOOT = [((15, 0, 3), (15, 10, 3), (20, 5, 3)),
                ((15, 0, 3), (15, 10, 3), (10, 5, 3))]
_DRAFTED_FOOT = [((15, 0, 3), (20, 5, 3), (18.536, 1.464, 3)),
                 ((15, 0, 3), (20, 5, 3), (11.464, 8.536, 3))]
CASES = {
    "seam_end_top_r1": ("s523", "boxcyl", ((2, 0, 10), (10, 0, 10)), 1.0, 1092.5263,
                        (2, 0, 10), (0.55, -1, 0.75)),
    "seam_end_bottom_r1": ("s523", "boxcyl", ((2, 0, 0), (10, 0, 0)), 1.0, 1092.5263,
                           (2, 0, 0), (0.55, -1, -0.75)),
    "seam_end_top_r0.5": ("s523", "boxcyl", ((2, 0, 10), (10, 0, 10)), 0.5, 1093.8183,
                          (2, 0, 10), (0.55, -1, 0.75)),
    "seam_end_top_r2": ("s523", "boxcyl", ((2, 0, 10), (10, 0, 10)), 2.0, 1087.3009,
                        (2, 0, 10), (0.55, -1, 0.75)),
    "slot_split_wall_r0.8": ("s962", "slotwall", ((10, 3, 5), (10, 3, 14)), 0.8, 1128.7639,
                             (10, 3, 5), (1, 0.9, 0.8)),
    "issue962_e101_r0.8": ("s962", "p962", ((50, 13.7, 22), (50, 13.7, 14)), 0.8, 11580.7739,
                           (50, 13.7, 14), (1, 0.9, 0.8)),
    "issue962_e50_r0.8": ("s962", "p962", ((38.5, 10.2, -3.75), (38.5, 10.2, 14)), 0.8,
                          11581.7204, (38.5, 10.2, 14), (-1, -1, 0.6)),
    "fin_on_block_r0.8": ("s962", "fin", ((10, 3, 5), (10, 3, 14)), 0.8, 768.7639,
                          (10, 3, 5), (1, 0.9, 0.8)),
    "arm_on_block_foot_r0.8": ("s962b", "armfoot", _FOOT, 0.8, 4603.6145,
                               (38.5, 10.2, -9.75), (-0.3, -1, -0.8)),
    "issue962_fillet_r0.8": ("s962b", "p962", _FILLET962, 0.8, 11552.7705,
                             (38.5, 10.2, -9.75), (-0.3, -1, -0.8)),
    "fin_on_block_wall_r0.8": ("s962c", "finwall", ((10, 3, 5), (10, 3, 14)), 0.8, 768.7639,
                               (10, 3, 5), (1, 0.9, 0.8)),
    "issue962_e36_r0.3": ("s962d", "p962", ((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)), 0.3,
                          None, (38.5, 27.2, -3.75), (-0.4, 1, 0.5)),
    "arm_on_tall_block_r0.3": ("s962d", "armtall", ((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)),
                               0.3, None, (38.5, 27.2, -3.75), (-0.4, 1, 0.5)),
    "issue962_e56_r0.8": ("s962e", "p962", ((38.5, 27.2, -3.75), (38.5, 27.2, 14)), 0.8,
                          11581.7068, (38.5, 27.2, -3.75), (-1, 1, 0.5)),
    "issue474_f003_e6_r0.8": ("s962e", "p474", ((-13, 0, 11), (-13, 0, 13)), 0.8, 1989.1235,
                              (-13, 0, 13), (-1, 1, 0.6)),
    "issue962_e33_r0.3": ("s962f", "p962", ((17.356038, -9.42499, -3.75), (38.5, 10.2, -3.75)),
                          0.3, 11583.5858, (38.5, 10.2, -3.75), (-1, -1, 0.6)),
    "slot_split_wall_r0.7001": ("s962g", "slotwall", ((10, 3, 5), (10, 3, 14)), 0.7001, 1129.0533,
                                (10, 3, 5), (1, 0.9, 0.8)),
    "fin_on_block_wall_r0.7": ("s962g", "finwall", ((10, 3, 5), (10, 3, 14)), 0.7, 769.0536,
                               (10, 3, 5), (1, 0.9, 0.8)),
    "mirror_top_r2": ("s523b", "boxcyl", ((0, 2, 10), (0, 10, 10)), 2.0, 1087.3009,
                      (0, 2, 10), (-1, 0.55, 0.75)),
    "arm_on_tall_block_whole_r2": ("s962h", "armwhole", ((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)),
                                   2.0, None, (38.5, 27.2, -3.75), (-0.4, 1, 0.5)),
    "post_on_plate_r0.6": ("s876", "postplate", ((-12, -3, 3), (0, -3, 3)), 0.6, 681.6610,
                           (0, -3, 3), (0.5, -1, 0.7)),
    "post_draft_on_plate_r0.6": ("s876b", "postdraft", ((-12, -3, 3), (0, -3, 3)), 0.6, 645.7228,
                                 (0, -3, 3), (0.5, -1, 0.7)),
    "post_seam_on_plate_r0.6": ("s876c", "postseam", ((-12, -3, 3), (0, -3, 3)), 0.6, 681.6610,
                                (0, -3, 3), (0.5, -1, 0.7)),
    "post_draft_plane_on_plate_r1": ("s876d", "postplane", ((-12, -3, 3), (0, -3, 3)), 1.0,
                                     754.5565, (-1, -2.5, 3), (0.3, -1, 0.7)),
    "issue876_corner4_r1": ("s894", "p876", [((17, 16.75, 0), (17, 16.75, 3)),
                                             ((-17, 16.75, 3), (17, 16.75, 3)),
                                             ((19.238761, 15.746985, 3), (17, 16.75, 3)),
                                             ((17, 16.75, 3), (17, 16.442791, 20.6))],
                            1.0, 8665.7912, (17, 16.75, 3), (0.6, 1, 0.7)),
    "seam_end_top_r2.5": ("s894", "boxcyl", ((2, 0, 10), (10, 0, 10)), 2.5, 1087.9914,
                          (2, 0, 10), (0.55, -1, 0.75)),
    "seam_end_top_r3": ("s894", "boxcyl", ((2, 0, 10), (10, 0, 10)), 3.0, 1086.0296,
                        (2, 0, 10), (0.55, -1, 0.75)),
    "issue962_rib_top_r0.8": ("s962i", "p962", ((35.5, 20.3, 32.25), (38.5, 20.3, 32.25)), 0.8,
                              11580.9213, (39.2, 20.3, 31.6), (0.6, 1, 0.7)),
    "slant_split_wall_r1.5": ("s962i", "slantblock", ((0, 0, 10), (4, 0, 10)), 1.5, 309.7450,
                              (5.5, 0, 9), (0.5, -1, 0.6)),
    "issue474_f003_e51_r0.8": ("s474", "p474", ((6.415306, 11.306805, 29.660692),
                                                 (6.415306, 11.306805, 38.0)), 0.8, 1987.7290,
                               (6.4, 11.3, 29.66), (-0.3, 1, 0.5)),
    "issue962_rib_foot_r1.5": ("s962j", "p962", ((35.5, 20.3, 32.25), (38.5, 20.3, 32.25)), 1.5,
                               11572.7267, (38.8, 20.0, 14.6), (-1, 0.6, -0.1)),
    "rib_foot_split_r1.5": ("s962j", "ribfoot", ((0, 3, 0), (-3, 3, 3)), 1.5, 536.1279,
                            (0.8, 3, 0.4), (0.6, 1, 0.6)),
    "seam_end_bottom_r2": ("s523c", "boxcyl", ((2, 0, 0), (10, 0, 0)), 2.0, 1087.3009,
                           (2, 0, 0), (0.55, -1, -0.75)),
    "rib_foot_split_r2.5": ("s962k", "ribfoot", ((0, 3, 0), (-3, 3, 3)), 2.5, 531.3115,
                            (0.8, 3, 0.4), (0.6, 1, 0.6)),
    "mirror_bottom_r2": ("s523c", "boxcyl", ((0, 2, 0), (0, 10, 0)), 2.0, 1087.3009,
                         (0, 2, 0), (-1, 0.55, -0.75)),
    "issue962_rib_foot_r0.9865": ("s962l", "p962", ((35.5, 20.3, 32.25), (38.5, 20.3, 32.25)),
                                  0.9865, 11579.2408, (38.8, 20.0, 14.6), (-1, 0.6, -0.1)),
    "issue523_bottom_rim_and_edge_a_r1": ("s523e", "boxcyl", [((2, 0, 0), (10, 0, 0)),
                                                              ((0, 2, 0), (2, 0, 0))],
                                          1.0, 1090.6315, (0, 1, 0), (-1, 0.55, -0.75)),
    "pinch_top_r2": ("s523d", "boxcyl", ((2, 0, 10), (10, 0, 10)), 2.0, 1087.3009,
                     (0, 2, 10), (-1, 0.55, 0.75)),
    "issue962_top_wall_r0.8": ("s962m", "p962", ((38.5, 10.2, -3.75), (38.5, 27.2, -3.75)), 0.8,
                               11586.4880, (38.5, 10.2, -3.75), (-0.5, -1, 0.6)),
    "ledge_wall_r0.8": ("s962m", "ledge", ((6, 3, 0), (6, 10, 0)), 0.8, 456.9737,
                        (6, 3, 0), (-0.5, -1, 0.6)),
    "issue474_f002_ramp_end_r0.3": ("s474b", "p474b", ((-5.4940374, 11.7820012, 13.0),
                                                        (-5.4940374, 11.7820012, 11.0)), 0.3,
                                    1939.2160, (-5.494, 11.782, 13.0), (0.35, 1, 0.5)),
    "issue962_hex_mouth_r0.8": ("s962n", "p962", ((38.8, 10.2, 24.4248711),
                                                   (38.8, 10.2, 19.5751289)), 0.8, 11583.5022,
                                (38.6, 10.2, 22.0), (-0.3, -1, 0.25)),
    "pocket_by_split_r0.8": ("s962n", "pocketsplit", ((5.3, 0, 3), (5.3, 0, 7)), 0.8, 577.8506,
                             (5.1, 0, 5), (-0.3, -1, 0.25)),
    "pocket_by_split_r0.3": ("s962o", "pocketsplit", ((5.3, 0, 3), (5.3, 0, 7)), 0.3, 578.3227,
                             (5.1, 0, 5), (-0.3, -1, 0.25)),
    "strip_box_r2": ("s962o", "stripbox", ((0, 0, 0), (0, 10, 0)), 2.0, 391.4159,
                     (0, 0, 0), (-1, -0.8, -0.7)),
    "arm_on_block_corner_upright_and_bottom_r1": (
        "s962r", "armfoot", [((50, 27.2, -3.75), (50, 27.2, -9.75)),
                             ((38.5, 27.2, -9.75), (50, 27.2, -9.75))], 1.0, 4599.7689,
        (38.5, 27.2, -9.75), (0.3, 1, -0.8)),
    "arm_on_block_far_top_edges_r1": (
        "s962s", "armfoot", [((17.356, -9.425, -3.75), (10.898, 16.471, -3.75)),
                             ((10.898, 16.471, -3.75), (38.5, 27.2, -3.75))], 1.0, 4591.4566,
        (10.898, 16.471, -3.75), (-1, 0.4, 0.8)),
    "slot_split_outer_floor_and_wall_r1": (
        "s962p", "slotouter", [((0, 3, 5), (10, 3, 5)), ((10, 3, 5), (10, 3, 14))], 1.0,
        1130.3068, (10, 3, 5), (1, 0.9, 0.8)),
    "arm_on_block_z-3.75_upright_and_block_r1": (
        "s962p", "armfoot", [((38.5, 10.2, -3.75), (38.5, 10.2, -9.75)),
                             ((38.5, 10.2, -3.75), (50, 10.2, -3.75))], 1.0, 4601.2153,
        (38.5, 10.2, -3.75), (-0.2, -1, 0.9)),
    "fin_on_block_x10_top_and_upright_r1": (
        "s962q", "fin", [((10, 3, 5), (10, 10, 5)), ((10, 3, 5), (10, 3, 14))], 1.0, 766.4705,
        (10, 3, 5), (1, 0.9, 0.8)),
    "issue962_hex_mouth_top_mouth_and_side_r0.3": (
        "s962t", "p962", [_HEXV + ((38.8, 10.2, 19.5751289),),
                          _HEXV + ((43, 10.2, 26.8497422),)], 0.3, 11583.9526,
        (38.8, 10.2, 24.42), (-0.3, -1, 0.25)),
    "issue962_hex_mouth_top_all_three_r1": (
        "s962u", "p962", [_HEXV + ((38.8, 10.2, 19.5751289),),
                          _HEXV + ((43, 10.2, 26.8497422),),
                          _HEXV + ((38.8, 11.7, 24.4248711),)], 1.0, 11582.1803,
        (38.8, 10.2, 24.42), (-0.3, -1, 0.25)),
    "pocket_by_split_corner_mouth_and_side_r1": (
        "s962v", "pocketsplit", [((5.3, 0, 3), (5.3, 0, 7)), ((5.3, 0, 3), (8, 0, 3))], 1.0,
        576.8663, (5.3, 0, 3), (-0.3, -1, 0.25)),
    "issue962_hex_mouth_top_side_and_inner_r1": (
        "s962w", "p962", [_HEXV + ((43, 10.2, 26.8497422),),
                          _HEXV + ((38.8, 11.7, 24.4248711),)], 1.0, 11583.2438,
        (38.8, 10.2, 24.42), (-0.3, -1, 0.25)),
    "issue962_hex_mouth_top_side_r1": (
        "s962x", "p962", _HEXV + ((43, 10.2, 26.8497422),), 1.0, 11583.1545,
        (38.8, 10.2, 24.42), (-0.3, -1, 0.25)),
    "fin_on_block_x10_all_three_r1": (
        "s962y", "fin", [((10, 3, 5), (10, 10, 5)), ((0, 3, 5), (10, 3, 5)),
                         ((10, 3, 5), (10, 3, 14))], 1.0, 768.7292, (10, 3, 5), (1, 0.9, 0.8)),
    "strip_box_r2.5": ("s962z", "stripbox", ((0, 0, 0), (0, 10, 0)), 2.5, 386.5874,
                       (0, 0, 0), (-1, -0.8, -0.7)),
    "slot_split_wall_mouth_r0.8": ("s962z", "slotwall", ((10, 3, 5), (10, 6, 5)), 0.8,
                                   1129.5880, (10, 3, 5), (1, 0.9, 0.8)),
    "slot_split_both_mouth_r0.8": ("s962za", "slotboth", ((10, 3, 5), (10, 6, 5)), 0.8,
                                   1129.5880, (10, 3, 5), (1, 0.9, 0.8)),
    "issue962_e72_r0.8": ("s962zb", "p962", ((38.5, 10.2, 14), (35.470838, 10.2, 17.029162)),
                          0.8, 11580.9704, (38.8, 10.2, 31.9), (0.5, -1, 0.7)),
    "slot_by_slope_r0.8": ("s962zc", "slotslope", ((0, 4, 5), (0, 7, 5)), 0.8, 937.0880,
                           (0, 4, 5), (-1, 0.9, 0.8)),
    "issue962_e52_r0.8": ("s962zc", "p962", ((38.5, 13.7, 14), (38.5, 17.1, 14)), 0.8,
                          11583.6729, (38.5, 13.7, 14), (-1, 0.9, 0.8)),
    "slot_by_slope_all_four_r1": (
        "s962zd", "slotslope", [((0, 0, 5), (0, 4, 5)), ((0, 4, 5), (0, 7, 5)),
                                ((0, 4, 5), (-5, 4, 10)), ((0, 4, 5), (0.7, 4, 5))],
        1.0, 937.5870, (0, 4, 5), (-1, 0.9, 0.8)),
    "slot_by_slope_floor_inline_r1": (
        "s962ze", "slotslope", [((0, 0, 5), (0, 4, 5)), ((0, 4, 5), (0.7, 4, 5))],
        1.0, 939.5563, (0, 4, 5), (-1, 0.9, 0.8)),
    "slot_by_slope_inline_slope_r1": (
        "s962zf", "slotslope", [((0, 0, 5), (0, 4, 5)), ((0, 4, 5), (-5, 4, 10))],
        1.0, 935.9822, (0, 4, 5), (-1, 0.9, 0.8)),
    "slot_by_slope_slope_floor_r1": (
        "s962zf", "slotslope", [((0, 4, 5), (-5, 4, 10)), ((0, 4, 5), (0.7, 4, 5))],
        1.0, 938.1564, (0, 4, 5), (-1, 0.9, 0.8)),
    "slot_split_both_floor_and_end_r1": (
        "s962zf", "slotboth", [((9.3, 3, 5), (10, 3, 5)), ((10, 3, 5), (10, 6, 5))],
        1.0, 1131.4815, (10, 3, 5), (1, 0.9, 0.8)),
    "slot_split_wall_top_and_upright_r1": (
        "s962zg", "slotwall", [((9.3, 3, 14), (10, 3, 14)), ((10, 3, 5), (10, 3, 14))],
        1.0, 1125.8785, (10, 3, 14), (1, 0.9, 0.8)),
    "issue962_rib_top_corner_r1": (
        "s962zg", "p962", [((35.5, 10.2, 32.25), (38.5, 10.2, 32.25)),
                           ((38.5, 13.7, 32.25), (38.5, 10.2, 32.25))],
        1.0, 11579.2314, (38.5, 10.2, 32.25), (0.5, -1, 0.7)),
    "pocket_mouth_upright_r2": ("s962zh", "pocketmouth", ((15.5, 0, 5), (15.5, 0, 10)), 2.0,
                                18485.2667, (16.2, 0, 6), (-0.6, 1, 0.8)),
    "issue962_pocket_edge_r2": (
        "s962zh", "p962", ((-10.68613441, -11.22748999, -5.8),
                           (-10.68613441, -11.22748999, -3.75)), 2.0, 11582.3197,
        (-11.3, -11.9, -6.5), (-0.3, 0.8, 0.6)),
    "fin_on_block_wall_top_and_upright_r1": (
        "s962zi", "finwall", [((10, 3, 5), (10, 10, 5)), ((10, 3, 5), (10, 3, 14))], 1.0,
        766.4705, (10, 3, 5), (1, 0.9, 0.8)),
    "arm_on_tall_block_near_split_down_r2": (
        "s962zj", "armnear", ((38.5, 10.2, -3.75), (38.5, 10.2, -9.75)), 2.0, 8074.1204,
        (38.5, 10.2, -3.75), (0.5, -1, 0.6)),
    "issue962_block_far_edge_over_arm_r2": (
        "s962zj", "p962", ((38.5, 27.2, -3.75), (38.5, 27.2, 14)), 2.0, 11569.2867,
        (38.5, 27.2, -3.75), (-1, 1, 0.5)),
    "arch_on_plate_foot_r0.8": ("s309", "arch", ((0, -10, 0), (0, 10, 0)), 0.8, 796.9055,
                                (0, -10, 0), (-1, -0.8, 0.7)),
    "arch_on_plate_split_foot_r0.8": ("s309b", "archsplit", ((0, -10, 0), (0, 10, 0)), 0.8,
                                      796.9055, (0, -10, 0), (-1, -0.8, 0.7)),
    "issue474_f002_wall_edge_r0.8": (
        "s474c", "p474b", ((-3.803564356, 8.156770083, 11.0), (-3.803564356, 8.156770083, 0.0)),
        0.8, 1937.9543, (-3.803564356, 8.156770083, 11.0), (0.9, -0.5, -0.3)),
    "arm_on_block_far_z-3.75_upright_and_block_r1": (
        "sarm", "armfoot", [((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)),
                            ((38.5, 27.2, -3.75), (50, 27.2, -3.75))], 1.0, 4600.9495,
        (38.5, 27.2, -3.75), (-0.3, 1, 0.6)),
    "issue962_rib_top_near_r1": (
        "srib", "p962", [((38.5, 13.7, 32.25), (38.5, 10.2, 32.25)),
                         ((38.5, 13.7, 32.25), (35.5, 13.7, 32.25))], 1.0, 11579.0926,
        (38.5, 13.7, 32.25), (0.5, 1, 0.7)),
    "fin_on_block_wall_piece_foot_and_top_r1": (
        "s962zl", "finwall", [((9.3, 3, 5), (10, 3, 5)), ((10, 3, 5), (10, 10, 5))], 1.0,
        770.7360, (10, 3, 5), (1, 0.9, 0.8)),
    "fin_on_block_wall_piece_foot_and_upright_r1": (
        "s962zl", "finwall", [((9.3, 3, 5), (10, 3, 5)), ((10, 3, 5), (10, 3, 14))], 1.0,
        770.3068, (10, 3, 5), (1, 0.9, 0.8)),
    "issue962_mouth_y17.1_floor_and_upright_r1.5": (
        "s962zl", "p962", [((49.308025, 17.1, 14), (50, 17.1, 14)),
                           ((50, 17.1, 14), (50, 17.1, 22))], 1.5, 11578.2359,
        (50, 17.1, 14), (1, -0.9, 0.8)),
    # seen from below: the face under the wall looks down
    "issue962_e36_r2": ("s962zk", "p962", ((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)), 2.0,
                        11584.0883, (38.5, 27.2, -3.75), (-0.35, 0.7, -1)),
    "arm_on_tall_block_whole_r0.8": (
        "s962zk", "armwhole", ((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)), 0.8, 8073.6686,
        (38.5, 27.2, -3.75), (-0.35, 0.7, -1)),
    "arm_tilted_under_block_skew_r2": (
        "s962zk", "armtilt", ((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)), 2.0, 7967.7871,
        (38.5, 27.2, -3.75), (-0.35, 0.7, -1)),
    # the foot's two arcs share their ends: each told by a point on it
    "boss_flush_foot_r1": ("sboss", "bossflush", [((15, 0, 3), (20, 5, 3), (18.536, 1.464, 3)),
                                                  ((15, 0, 3), (20, 5, 3), (11.464, 8.536, 3))],
                           1.0, 2591.8420, (15, 0, 3.5), (0.35, -1, 0.5)),
    # the same boss drafted, its foot as the cylinder's; filleted and chamfered
    "boss_drafted_flush_foot_r1": ("sdraftboss", "bossdrafted", _DRAFTED_FOOT, 1.0, 2443.9037,
                                   (15, 0, 3.5), (0.35, -1, 0.5)),
    "boss_drafted_chamfer_r1": ("sdraftboss", "bossdrafted", _DRAFTED_FOOT, 1.0, 2453.7582,
                                (15, 0, 3.5), (0.35, -1, 0.5)),
    # the post's long wall on #876's plate, drafted 1 deg and flush with the
    # plate's side at its foot: a fillet 0.005 wide, cut at x=4.043 and 9.143 where it
    # was not a point
    "issue876_kink_e52_r0.3": ("sthin", "p876", ((-17, -16.75, 3), (17, -16.75, 3)), 0.3,
                               8665.7839, (4.043, -16.75, 3), (0.3, -1, 0.4)),
    # the flush boss turned a quarter: the foot in two equal halves, the walk
    # past the point stopped at the seam with the spine end's parameter
    "boss_flush_halves_foot_r1": ("shalves", "bosshalves", _HALVES_FOOT, 1.0, 2591.8420,
                                  (15, 0, 3.5), (0.35, -1, 0.5)),
    # turned three quarters: the seam up from the point, split where the
    # fillet's line meets it
    "boss_flush_seam_foot_r1": ("sseam", "bossseam", [((15, 0, 3), (15, 0, 3), (20, 5, 3))], 1.0,
                                2591.8420, (15, 0, 3.5), (0.35, -1, 0.5)),
    # #474's step along its top, two faces 1.5 deg apart: the fillet's line on
    # the top ran on past the corner (-13,0,13) as far as the surface was
    # carried; refused there now, and the corner set back
    "issue474_f003_run_on_e2_r0.3": ("srunon", "p474", ((-13, 0, 13), (-9, 0, 13)), 0.3,
                                     1988.8707, (-13, 0, 13), (-1, -1, 0.6)),
    # #273's pocket in the handle's top, its apex 22 deg: the fillet's end
    # ran off the top, and the corner set back made a patch across the apex
    # that folded over itself; refused at 31cf3ce134, as upstream refuses
    # it, and made since soff (below)
    "issue273_pocket_apex_fold_e23_r0.8": ("sfold", "p273", ((0, 15.013479, 31),
                                                             (1.524712, 7.124642, 31)), 0.8,
                                           8558.3169, (0.2, 14.6, 30.7), (1, -0.5, 1.1)),
    # the same: the cap in the other wall runs off the top, and the cut is
    # carried on into the handle's end, the groove running out through it
    "issue273_pocket_apex_off_e23_r0.8": ("soff", "p273", ((0, 15.013479, 31),
                                                           (1.524712, 7.124642, 31)), 0.8,
                                          8558.3169, (0.2, 14.6, 30.7), (1, -0.5, 1.1)),
    # the same with the flat end at a vertex (FLAT): the fillet ends at the
    # apex in a flat face square to the rim, nothing past the pocket cut
    "issue273_pocket_flat_e23_r0.8": ("sflat", "p273", ((0, 15.013479, 31),
                                                       (1.524712, 7.124642, 31)), 0.8,
                                      8558.3813, (0.2, 14.6, 30.7), (1, -0.5, 1.1)),
    # #273's handle on the cup's top, its side's foot: the fillet ends where
    # the handle's front stands on the cup's rim, and the piece of the rim
    # from the vertex to the fillet's end came out the wrong way round
    "issue273_handle_foot_e11_r0.8": ("shandle", "p273", ((2.3338652, 16.5866083, 18),
                                                          (5.4331299, -15.8443554, 18)), 0.8,
                                      8563.6287, (5.5, -15.6, 18.3), (1, -0.8, 0.8)),
    # #474's Fillet002, the upright edge at the sliver of a top: the piece of
    # the top's long edge kept was the far end's, the corner left in the top
    "issue474_f002_sliver_top_r0.3": ("ssliver", "p474b", ((-7.306653, 10.9367647, 13),
                                                          (-7.306653, 10.9367647, 0)), 0.3,
                                      1939.2197, (-7.25, 10.9, 12.85), (-0.6, 0.3, 1)),
    # x16win's chamfer, run on along the mitre of two fillets to their corner
    # (2,30,8), where both turn flush with the back face; the radius is the
    # larger distance (CHAMFER has them)
    "chamfer_fillet_corner_poly": ("schamfer", "chfcorner", ((0, 0, 10), (0, 28, 10)), 1.0,
                                   11909.6170, (2.4, 30, 7.6), (-0.5, 1, 0.6)),
    "chamfer_fillet_corner_box": ("schamfer", "chfcornerbox", ((0, 0, 10), (0, 28, 10)), 1.0,
                                  11909.6170, (2.4, 30, 7.6), (-0.5, 1, 0.6)),
    "chamfer_fillet_corner_poly_1_1.5": ("schamfer", "chfcorner", ((0, 0, 10), (0, 28, 10)),
                                         1.5, 11901.8128, (2.6, 30, 7.4), (-0.5, 1, 0.6)),
}
# case -> the chamfer's distances: makeChamfer in place of makeFillet
CHAMFER = {
    "chamfer_fillet_corner_poly": (1.0,),
    "chamfer_fillet_corner_box": (1.0,),
    "chamfer_fillet_corner_poly_1_1.5": (1.0, 1.5),
    "boss_drafted_chamfer_r1": (1.0,),
}
# case -> (the largest tolerance it may carry, how far its volume may be off):
# a result is also held to these and to BOP's check (Shape.check(True)), where
# valid is not enough to tell before from after
STRICT = {
    "issue962_e36_r2": (1e-6, 1e-4),
    "arm_on_tall_block_whole_r0.8": (1e-6, 1e-4),
    "arm_tilted_under_block_skew_r2": (1e-6, 1e-4),
    "fin_on_block_wall_piece_foot_and_top_r1": (2e-4, 1e-3),
    "chamfer_fillet_corner_poly": (1e-4, 1e-3),
    "chamfer_fillet_corner_box": (1e-4, 1e-3),
    "chamfer_fillet_corner_poly_1_1.5": (1e-4, 1e-3),
    "fin_on_block_wall_piece_foot_and_upright_r1": (2e-4, 1e-3),
    "issue962_mouth_y17.1_floor_and_upright_r1.5": (2e-4, 1e-3),
    "boss_drafted_flush_foot_r1": (1e-4, 1e-3),
    "boss_drafted_chamfer_r1": (1e-4, 1e-3),
    "issue876_kink_e52_r0.3": (1e-3, 1e-3),
    "boss_flush_halves_foot_r1": (1e-4, 1e-3),
    "boss_flush_seam_foot_r1": (1e-4, 1e-3),
    "issue474_f003_run_on_e2_r0.3": (2e-4, 1e-3),
    "issue273_pocket_apex_fold_e23_r0.8": (0.031, 1e-3),
    "issue273_pocket_apex_off_e23_r0.8": (0.031, 1e-3),
    "issue273_pocket_flat_e23_r0.8": (0.031, 1e-4),
    "issue273_handle_foot_e11_r0.8": (0.031, 1e-3),
    "issue474_f002_sliver_top_r0.3": (1e-4, 1e-4),
}
# cases made with the flat end at a vertex (ChFi3d_Builder::SetFlatEndAtVertex,
# ../../flat_end.py), where the OCCT has it
FLAT = {"issue273_pocket_flat_e23_r0.8"}
# case -> (the zoomed row's label, its colour), when it is not "the fillet's
# end" in grey: a view from below is dark where the label goes
# cases whose fix refuses the fillet: refused is the answer expected (the
# "after" column), a result made is not
REFUSED = set()
ZOOMLABEL = {
    "chamfer_fillet_corner_poly": ("the chamfer's end", (110, 110, 110)),
    "chamfer_fillet_corner_box": ("the chamfer's end", (110, 110, 110)),
    "chamfer_fillet_corner_poly_1_1.5": ("the chamfer's end", (110, 110, 110)),
    "boss_drafted_chamfer_r1": ("the chamfer's end", (110, 110, 110)),
    "issue876_kink_e52_r0.3": ("where the old fillet was first cut, x=4.043", (110, 110, 110)),
    "issue962_e36_r2": ("the fillet's end, from below", (240, 240, 240)),
    "arm_on_tall_block_whole_r0.8": ("the fillet's end, from below", (240, 240, 240)),
    "arm_tilted_under_block_skew_r2": ("the fillet's end, from below", (240, 240, 240)),
}
# case -> the zoomed row's height, when 4 r + 3 shows too little (a shallow edge)
ZOOM = {
    # the fillet is 0.005 wide; the old one's first cut at x=4.043
    "issue876_kink_e52_r0.3": 0.04,
    "issue962_e36_r2": 1.4,
    "arm_on_tall_block_whole_r0.8": 0.6,
    "arm_tilted_under_block_skew_r2": 1.4,
    "issue962_e36_r0.3": 0.5,
    "arm_on_tall_block_r0.3": 0.5,
    "issue962_e33_r0.3": 0.5,
    "arm_on_tall_block_whole_r2": 3.0,
    # the sliver of a top, 0.155 wide at the vertex
    "issue474_f002_sliver_top_r0.3": 1.2,
}
# multi-edge case -> what its edges are, for the picture's heading
EDGES = {
    "fin_on_block_wall_piece_foot_and_top_r1": "the 0.7 piece of the edge under the fin's wall "
                                               "and the block's top edge on the side x=10",
    "fin_on_block_wall_piece_foot_and_upright_r1": "the 0.7 piece of the edge under the fin's "
                                                   "wall and the fin's upright edge",
    "issue962_mouth_y17.1_floor_and_upright_r1.5": "the 0.69 piece of the floor's edge along "
                                                   "the rib and the rib's upright edge",
    "slot_by_slope_floor_inline_r1": "the floor's on the wall, the side's under the slope",
    "slot_by_slope_inline_slope_r1": "the side's under the slope, the slope's on the wall",
    "slot_by_slope_slope_floor_r1": "the slope's on the wall, the floor's on the wall",
    "slot_split_both_floor_and_end_r1": "the floor's along the wall, the floor's on the outer "
                                        "face",
    "slot_split_wall_top_and_upright_r1": "the wall's piece's top edge and its upright one",
    "issue962_rib_top_corner_r1": "the top's two edges at the rib's corner, (38.5, 10.2, 32.25)",
    "slot_by_slope_all_four_r1": "the four at the slot's corner, (0, 4, 5)",
    "arm_on_block_foot_r0.8": "the two at the foot, x=38.5, y=27.2 and y=10.2",
    "issue962_fillet_r0.8": "the Fillet's twelve; zoomed on edge 49's foot",
    "issue876_corner4_r1": "the four at the corner (17,16.75,3); zoomed on it",
    "arm_on_block_corner_upright_and_bottom_r1": "the block's upright edge at (50,27.2) and "
                                                 "its bottom edge to the arm; zoomed on "
                                                 "that edge's far end",
    "arm_on_block_far_top_edges_r1": "the arm's two top edges at its far end",
    "slot_split_outer_floor_and_wall_r1": "the slot's floor edge and its wall's edge on "
                                          "the outer face",
    "arm_on_block_z-3.75_upright_and_block_r1": "the upright edge where arm and block meet "
                                                "and the block's top edge from it",
    "fin_on_block_x10_top_and_upright_r1": "the block's top edge and the fin's upright edge "
                                           "on the side x=10",
    "issue962_hex_mouth_top_mouth_and_side_r0.3": "the mouth's edge beside the split and the "
                                                  "next, at the mouth's top corner",
    "issue962_hex_mouth_top_all_three_r1": "the three at the mouth's top corner",
    "pocket_by_split_corner_mouth_and_side_r1": "the mouth's edge beside the split and its "
                                                "bottom edge",
    "issue962_hex_mouth_top_side_and_inner_r1": "the mouth's second edge from the split and "
                                                "the pocket's inner edge, at the top corner",
    "fin_on_block_x10_all_three_r1": "the block's top edge, the fin's upright edge and the "
                                     "concave edge between fin and block, at (10,3,5)",
    "fin_on_block_wall_top_and_upright_r1": "the block's top edge and the fin's upright edge "
                                            "on the side x=10, the fin's wall split 0.7 from it",
    "arm_on_block_far_z-3.75_upright_and_block_r1": "the upright edge between arm and block "
                                                    "and the block's top edge from it, at y=27.2",
    "issue962_rib_top_near_r1": "the top's two edges at the rib's corner beside the split "
                                "wall, (38.5, 13.7, 32.25)",
    "issue523_bottom_rim_and_edge_a_r1": "the cylinder's rim and the box's bottom edge from it",
    "boss_flush_foot_r1": "the boss's foot, its two arcs",
    "boss_drafted_flush_foot_r1": "the boss's foot, its two arcs",
    "boss_drafted_chamfer_r1": "the boss's foot, its two arcs",
    "boss_flush_halves_foot_r1": "the boss's foot, its two halves",
    "boss_flush_seam_foot_r1": "the boss's foot, one closed edge",
    "issue474_f003_run_on_e2_r0.3": "the step's edge along the top, (-13,0,13)-(-9,0,13)",
}


def edge_between(shape, a, b, via=None):
    """The edge from a to b; of several, the one passing nearest <via>. A
    closed edge is the one from its vertex to itself, a == b."""
    want = sorted({tuple(round(c, 6) for c in a), tuple(round(c, 6) for c in b)})
    found = [e for e in shape.Edges
             if sorted({tuple(round(c, 6) for c in v.Point) for v in e.Vertexes}) == want]
    if not found:
        raise ValueError("no edge between %s and %s" % (a, b))
    if via is None or len(found) == 1:
        return found[0]
    p = Part.Vertex(App.Vector(*via))
    return min(found, key=lambda e: e.distToShape(p)[0])
