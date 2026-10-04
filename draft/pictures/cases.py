# The cases models/Draft.md shows, and how each is drafted.
#
# A case: (stage, shape, face, neutral, angle, focus, zoom, eye, note)
#   stage    the fix that changed it (STAGES)
#   shape    a key of SHAPES
#   face     the face to draft, neutral the face whose plane is the neutral
#            plane (its normal the pull direction, as PartDesign's Draft
#            takes it): an index into the shape's Faces (1-based), or a
#            predicate
#   angle    degrees
#   focus    the point the second row zooms on, zoom its view's height
#   eye      the direction the views look from (ZOOM_EYE: the second row's)
#   note     what the case shows, under its name
# A "doc:" shape is a Draft feature of a document, recomputed alone.
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.join(HERE, "..", "..")

# stage: (the fork just before the fix, the fix)
STAGES = {
    "d334": ("18dfed534b", "ca766a8a92"),
    "d474": ("0b66de96f5", "f9d329a663"),
    "dtopo": ("ccc62e7003", "a5c8b99e38"),
}
# Upstream: the Draft package as OCCT 8.0.1 has it -- the fork had not
# touched it before d334, so its files at d334's "before" are upstream's.
UPSTREAM = "18dfed534b"
# The files a stage library takes from its commit; the rest of TKOffset is
# the fork's as built.
DRAFT_FILES = [
    "src/ModelingAlgorithms/TKOffset/Draft/Draft_Modification.cxx",
    "src/ModelingAlgorithms/TKOffset/Draft/Draft_Modification_1.cxx",
    "src/ModelingAlgorithms/TKOffset/BRepOffsetAPI/BRepOffsetAPI_DraftAngle.cxx",
]


def _plane_at(axis, value, lo=None):
    def pick(f):
        if f.Surface.__class__.__name__ != "Plane":
            return False
        b = f.BoundBox
        a = axis.upper()
        if abs(getattr(b, a + "Min") - value) > 1e-9 or abs(getattr(b, a + "Max") - value) > 1e-9:
            return False
        if lo:
            ax, x0, x1 = lo
            return (getattr(b, ax.upper() + "Min") > x0 - 1e-9
                    and getattr(b, ax.upper() + "Max") < x1 + 1e-9)
        return True
    return pick


def _notch(bevel):
    import FreeCAD as App
    import Part
    V = App.Vector
    s = Part.makeBox(20, 10, 10).cut(Part.makeBox(10, 5, 5, V(0, 0, 5)))
    if bevel:
        w = Part.Face(Part.makePolygon([V(10, 0, 5), V(10, -1, 5), V(10, -1, 11),
                                        V(10, 4.8, 11), V(10, 0, 5)])).extrude(V(11, 0, 0))
        s = s.cut(w)
    return s.removeSplitter()


def _slot():
    import FreeCAD as App
    import Part
    return Part.makeBox(20, 20, 20).cut(
        Part.makeBox(4, 6, 18, App.Vector(8, 2, 2))).removeSplitter()


def _split_floor():
    import FreeCAD as App
    import Part
    V = App.Vector
    p = Part.Face(Part.makePolygon([V(0, -5, 0), V(10, 0, 0), V(10, 10, 0), V(0, 10, 0),
                                    V(0, -5, 0)])).extrude(V(0, 0, 5))
    return p.fuse(Part.makeBox(10, 10, 5, V(10, 0, 0)))


def _brep(path):
    def make():
        import Part
        return Part.read(path)
    return make


SHAPES = {
    "notch": lambda: _notch(False),
    "notch_bevel": lambda: _notch(True),
    "slot": _slot,
    "split_floor": _split_floor,
    "slot_wall_split": _brep(os.path.join(HERE, "..", "models", "slot_wall_split.brep")),
    "issue962_pocket002": _brep(os.path.join(FORK, "fillet", "models", "issue962_pocket002.brep")),
    "issue474_fillet003": _brep(os.path.join(FORK, "fillet", "models",
                                             "issue474_fillet003_base.brep")),
}
NAMES = {
    "notch": "a 20x10x10 block, a 10x5x5 notch off its front top",
    "notch_bevel": "the notched block, its front top edge right of the notch bevelled to the ledge's corner",
    "slot": "a 20 cube, a 4x6 slot 18 deep, 2 from the front",
    "split_floor": "a prism whose front wall meets a slanted wall, floor and top split along x=10 (two solids fused)",
    "slot_wall_split": "a block with a slot, the slot's front wall split in two coplanar pieces at x=9.3",
    "issue962_pocket002": "realthunder/FreeCAD#962's Pocket002",
    "issue474_fillet003": "realthunder/FreeCAD#474 Fillet003's input",
}
# a document's Draft: (file, object) -- none pictured now: #334's Draft001 has
# its faults inside the part, where no view reaches; notch_bevel_ledge is the
# same corner, in the open.
DOCS = {}
# the zoomed row's direction, where it is not the case's own
ZOOM_EYE = {"split_floor_corner_a5": (0, 0, 1)}
# a case drafted first at another angle, as the task panel does
PRE_ANGLE = {"issue474_ramp_ledge_a15": 1}

FRONT = (-1, -1.6, 1.2)
CASES = {
    # d334
    "notch_bevel_ledge_a20": ("d334", "notch_bevel", _plane_at("z", 5), _plane_at("y", 5), 20,
                              (10, 0, 7), 8, FRONT,
                              "the ledge drafted about the notch's back wall; the bevel touches its corner"),
    # d474
    "issue474_ramp_ledge_a15": ("d474", "issue474_fillet003", 3, 10, 15, (-13, 0, 14), 14,
                                (-1, -1.4, 1.1),
                                "the ledge top drafted about its end wall, recomputed in the base's frame"),
    # dtopo
    "slot_wall_a5": ("dtopo", "slot", _plane_at("y", 2), _plane_at("z", 2), 5, (10, 2, 18), 12,
                     (0.5, -1, 1.6), "the slot's front wall drafted about the slot's floor"),
    "slot_wall_a15": ("dtopo", "slot", _plane_at("y", 2), _plane_at("z", 2), 15, (10, 0, 18), 12,
                      (0.5, -1, 1.6), "the same past 6.3 deg: its top would pass the block's front"),
    "split_floor_corner_a5": ("dtopo", "split_floor", _plane_at("y", 0), _plane_at("x", 20), 5,
                              (9.3, -0.3, 5), 4, (-0.6, -1, 1.3),
                              "the front wall drafted about the end wall x=20"),
    "slot_wall_split_piece_a5": ("dtopo", "slot_wall_split", 3, 1, 5, (5, 3, 10), 12,
                                 (0.4, 0.5, 1.2),
                                 "the long piece drafted about the side x=0, through its split edge"),
    "notch_ledge_a44": ("dtopo", "notch", _plane_at("z", 5), _plane_at("y", 5), 44, (10, 0, 9),
                        5, FRONT, "the ledge drafted about the notch's back wall, short of the top"),
    "notch_ledge_a45": ("dtopo", "notch", _plane_at("z", 5), _plane_at("y", 5), 45, (10, 0, 9),
                        5, FRONT, "the same at 45 deg: the ledge's edge reaches the block's top"),
    "issue962_f41_n24_a5": ("dtopo", "issue962_pocket002", 41, 24, 5, (50, 12.5, 22), 6,
                            (1, -0.8, 1), "face 41 drafted about face 24, a chamfer's plane"),
}
