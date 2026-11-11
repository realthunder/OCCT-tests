# FreeCAD (GUI, under xvfb-run) issue334_arc_reference_picture.py
#
# The panels of the picture of README.md's "A face not found again for its
# arc": the two shapes issue334_arc_reference_shapes.py wrote to $OUT, both
# from the drafted ledges' side, faces that fail isValid() in red. Writes
# $OUT/issue334_{stored,recomputed}.png; issue334_arc_reference_compose.py
# lays them out.
import os, json
import FreeCAD as App, FreeCADGui as Gui, Part
from PySide6 import QtCore
V = App.Vector
OUT = os.environ.get("OUT", os.path.dirname(os.path.abspath(__file__)))
App.ParamGet("User parameter:BaseApp/Preferences/Document").SetInt("TransactionLog", 0)
Gui.showMainWindow() if not Gui.getMainWindow() else None
def camera(eye, up, center, height):
    z = V(eye); z.normalize()
    y = up - z * up.dot(z); y.normalize()
    x = y.cross(z)
    r = App.Rotation(App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0))
    pos = center + z * 1000
    return ("#Inventor V2.1 ascii\nOrthographicCamera {\n viewportMapping ADJUST_CAMERA\n"
            " position %g %g %g\n orientation %g %g %g %g\n nearDistance 1\n farDistance 3000\n"
            " aspectRatio 1\n focalDistance 1000\n height %g\n}\n"
            % (pos.x, pos.y, pos.z, r.Axis.x, r.Axis.y, r.Axis.z, r.Angle, height))
def env(name, default):
    return [float(x) for x in os.environ.get(name, default).split(",")]
info = {}
for name in ("stored", "recomputed"):
    shape = Part.Shape(); shape.read(os.path.join(OUT, "issue334_%s.brep" % name))
    doc = App.newDocument("P")
    o = doc.addObject("Part::Feature", "S"); o.Shape = shape
    doc.recompute()
    vo = o.ViewObject
    bad = [i for i, f in enumerate(shape.Faces) if not f.isValid()]
    cols = [(0.72, 0.76, 0.82, 1.0)] * len(shape.Faces)
    for i in bad: cols[i] = (0.9, 0.1, 0.1, 1.0)
    vo.DiffuseColor = cols
    vo.LineColor = (0.1, 0.1, 0.1); vo.LineWidth = 1.5; vo.PointSize = 1
    info[name] = len(bad)
    view = Gui.ActiveDocument.ActiveView
    view.setCamera(camera(V(*env("EYE", "0.9,-1,0.75")), V(0, 0, 1),
                          V(*env("CENTER", "8,24,48")), env("HEIGHT", "105")[0]))
    for _ in range(5): Gui.updateGui()
    view.saveImage(os.path.join(OUT, "issue334_%s.png" % name), 900, 800, "White")
    App.closeDocument(doc.Name)
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
os.write(1, ("\nPIC " + json.dumps(info) + "\n").encode())
os._exit(0)
