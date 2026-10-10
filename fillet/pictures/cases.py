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
}
# stage -> the toolkits its "before" library is built of, when not TKFillet alone
STAGE_TOOLKITS = {
    "s962d": "TKFillet TKGeomAlgo",
}
# Upstream: the toolkit's files that differ from the fork, at the fork's base --
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


def _fin():
    # run_tests.py's fin padded flush with the block's side
    V = App.Vector
    return Part.makeBox(10, 10, 5).fuse(Part.makeBox(10, 3, 9, V(0, 0, 5)))


def _fin_wall():
    # the fin, its wall split 0.7 from the outer face as the slot's
    V = App.Vector
    return _fin().generalFuse([Part.LineSegment(V(9.3, 3, 5), V(9.3, 3, 20)).toShape()])[0].Solids[0]


def _arm_on_tall_block(split=True):
    # run_tests.py's arm fused to a block that goes on above it, the block's
    # side y=27.2 two faces split at the arm's top (or one face)
    V = App.Vector
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 6))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    s = Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 23.75)).fuse(arm)
    if not split:
        return s
    cut = Part.LineSegment(V(38.5, 27.2, -3.75), V(50, 27.2, -3.75)).toShape()
    return s.generalFuse([cut])[0].Solids[0]


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


SHAPES = {
    "boxcyl": _brep("issue523_box_cylinder.brep"),
    "slotwall": _slot_wall,
    "p962": _brep("issue962_pocket002.brep"),
    "fin": _fin,
    "finwall": _fin_wall,
    "armfoot": _arm_on_block,
    "armtall": _arm_on_tall_block,
    "armwhole": lambda: _arm_on_tall_block(split=False),
    "p474": _brep("issue474_fillet003_base.brep"),
    "postplate": _post_on_plate,
    "postdraft": lambda: _post_on_plate(draft=1.0),
    "postseam": lambda: _post_on_plate(turn=270),
    "postplane": _teardrop_post_on_plate,
    "p876": _brep("issue876_fillet_base.brep"),
    "slantblock": _slant_block,
    "ribfoot": _rib_foot,
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


# shape -> the face whose (u, v) outline the third row draws, found in a result
UVFACE = {
    # the corner's cylinder, not a fillet of the same radius
    "boxcyl": (lambda f: f.Surface.__class__.__name__ == "Cylinder"
               and abs(f.Surface.Radius - 2) < 1e-6 and abs(abs(f.Surface.Axis.z) - 1) < 1e-9),
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
    # the corner's plate at edge 6's top
    "p474": _plate_near(-13, 0, 13),
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
}
# case -> a third-row face other than its shape's
UVFACE_CASE = {
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
}
NAMES = {
    "boxcyl": "10 box with a 3/4 cylinder r2 at a corner (#523, Part Connect)",
    "slotwall": "10x10x14 block, a slot down to z=5, the slot's wall two faces split 0.7 "
                "from the outer face",
    "p962": "#962's Pocket002, the Fillet's input (a PartDesign body without Refine)",
    "fin": "10x10x5 block with a 10x3x9 fin padded flush with its side x=10",
    "finwall": "the fin flush with the block, its wall two faces split 0.7 from the outer face",
    "armfoot": "an arm fused to an 11.5x17x6 block, their bottoms two faces split along x=38.5",
    "armtall": "the arm fused to an 11.5x17x23.75 block, the block's side y=27.2 two faces "
               "split at the arm's top",
    "armwhole": "the arm fused to an 11.5x17x23.75 block, the block's side y=27.2 one face",
    "p474": "#474's Fillet003 input (a PartDesign body)",
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
}
# shape -> the whole shape's view: (center, height)
VIEW = {
    "boxcyl": ((4, 4, 5), 19.0),  # the box and cylinder span -2..10 on each axis
    "slotwall": ((5, 5, 7), 20.0),
    "p962": ((16, 4, 11), 62.0),
    "fin": ((5, 5, 7), 20.0),
    "finwall": ((5, 5, 7), 20.0),
    "armfoot": ((30, 9, -6.75), 42.0),
    "armtall": ((30, 9, 2), 46.0),
    "armwhole": ((30, 9, 2), 46.0),
    "p474": ((-1.4, 0, 24.3), 34.0),
    "postplate": ((-4.5, 0, 9), 20.0),
    "postdraft": ((-4.5, 0, 9), 20.0),
    "postseam": ((-4.5, 0, 9), 20.0),
    "postplane": ((-4.5, 0, 9), 20.0),
    "p876": ((0, 0, 10), 46.0),
    "slantblock": ((6, 1.5, 5), 14.0),
    "ribfoot": ((3.5, 3, 2), 16.0),
}
# shape -> (what the third row's face is, whether to draw u gridlines at pi/2)
UVLABEL = {
    "boxcyl": ("the cylinder face", True),
    "slotwall": ("the slot's floor", False),
    "p962": ("the face at the fillet's end", False),
    "fin": ("the fin's outer face", False),
    "finwall": ("the block's top", False),
    "armfoot": ("the arm's bottom", False),
    "armtall": ("the corner's plate", False),
    "armwhole": ("the arm's top", False),
    "p474": ("the corner's plate", False),
    "postplate": ("the plate's side", False),
    "postdraft": ("the post's cone", False),
    "postseam": ("the post's cylinder", True),
    "postplane": ("the post's wall beyond the cone", False),
    "p876": ("the corner's plate", False),
    "slantblock": ("the wall's second piece", False),
    "ribfoot": ("the block's top", False),
}
# case -> the same, when its face is not the shape's (UVFACE_CASE)
UVLABEL_CASE = {
    "issue962_rib_top_r0.8": ("the rib's wall, its second piece", False),
    "issue962_rib_foot_r1.5": ("the block's top at the rib's foot", False),
    "issue474_f003_e51_r0.8": ("the face at the fillet's end", False),
    "slot_split_wall_r0.7001": ("the block's top beside the slot", False),
    "seam_end_top_r2.5": ("the corner's plate", False),
    "seam_end_top_r3": ("the corner's plate", False),
    "issue962_rib_foot_r0.9865": ("the block's top at the rib's foot", False),
    "pinch_top_r2": ("the top, the box's part", False),
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
                            1.0, 8665.7870, (17, 16.75, 3), (0.6, 1, 0.7)),
    "seam_end_top_r2.5": ("s894", "boxcyl", ((2, 0, 10), (10, 0, 10)), 2.5, 1085.6014,
                          (2, 0, 10), (0.55, -1, 0.75)),
    "seam_end_top_r3": ("s894", "boxcyl", ((2, 0, 10), (10, 0, 10)), 3.0, 1072.1768,
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
    "pinch_top_r2": ("s523d", "boxcyl", ((2, 0, 10), (10, 0, 10)), 2.0, 1087.3009,
                     (0, 2, 10), (-1, 0.55, 0.75)),
}
# case -> the zoomed row's height, when 4 r + 3 shows too little (a shallow edge)
ZOOM = {
    "issue962_e36_r0.3": 0.5,
    "arm_on_tall_block_r0.3": 0.5,
    "issue962_e33_r0.3": 0.5,
    "arm_on_tall_block_whole_r2": 3.0,
}
# multi-edge case -> what its edges are, for the picture's heading
EDGES = {
    "arm_on_block_foot_r0.8": "the two at the foot, x=38.5, y=27.2 and y=10.2",
    "issue962_fillet_r0.8": "the Fillet's twelve; zoomed on edge 49's foot",
    "issue876_corner4_r1": "the four at the corner (17,16.75,3); zoomed on it",
}


def edge_between(shape, a, b):
    want = sorted([tuple(round(c, 6) for c in a), tuple(round(c, 6) for c in b)])
    for i, e in enumerate(shape.Edges):
        if sorted(tuple(round(c, 6) for c in v.Point) for v in e.Vertexes) == want:
            return e
    raise ValueError("no edge between %s and %s" % (a, b))
