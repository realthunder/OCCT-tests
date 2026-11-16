# shapes3.py -- shapes the thickness scan (scan.py, SET=3) takes besides the
# probe's two sets: boxes of 30 x 20 x 10 with their top edges chamfered
# unevenly (README.md sec 83) and one with a notch across a corner (sec 84).
import FreeCAD, Part

V = FreeCAD.Vector


def _chamfered(d1, d2):
    b = Part.makeBox(30, 20, 10)
    top = [
        e for e in b.Edges if abs(e.BoundBox.ZMin - 10) < 1e-9 and abs(e.BoundBox.ZMax - 10) < 1e-9
    ]
    return b.makeChamfer(d1, d2, top)


def notch_corner():
    # the prism extruded down from the top: extruded up from the notch's
    # floor, the box does not show sec 84's fault
    notch = Part.Face(Part.makePolygon([V(0, 0, 10), V(6, 0, 10), V(0, 9, 10), V(0, 0, 10)]))
    return Part.makeBox(30, 20, 10).cut(notch.extrude(V(0, 0, -4)))


SHAPES = {
    "chamfer_2x1": lambda: _chamfered(2, 1),
    "chamfer_2x2": lambda: _chamfered(2, 2),
    "chamfer_1x3": lambda: _chamfered(1, 3),
    "notch_corner": notch_corner,
}
