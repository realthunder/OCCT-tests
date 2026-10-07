# FreeCAD (GUI) panel_shot.py -- the fillet task panel editing a setback
# corner, its handles in the view: a screenshot of the main window to $SHOT.
# Run as a macro (make_corners.sh).
import os
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

V = App.Vector


def emit(s):
    os.write(1, (s + "\n").encode())


def wait(sec):
    end = time.time() + sec
    while time.time() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.02)


def _look(eye):
    """The camera orientation looking from eye toward the origin, z up"""
    z = V(*eye)
    z.normalize()
    y = V(0, 0, 1) - z * z.z
    y.normalize()
    x = y.cross(z)
    return App.Rotation(App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0))


def shot():
    App.ParamGet("User parameter:BaseApp/Preferences/View").SetBool("ShowNaviCube", False)
    mw = Gui.getMainWindow()
    mw.showNormal()
    mw.resize(1500, 800)
    doc = App.newDocument("Corners")
    body = doc.addObject("PartDesign::Body", "Body")
    box = body.newObject("PartDesign::AdditiveBox", "Box")
    doc.recompute()
    corner = [v for v in box.Shape.Vertexes if v.Point.isEqual(V(10, 10, 10), 1e-7)][0]
    vname = "Vertex%d" % box.Shape.findSubShape(corner)[1]
    edges = ["Edge%d" % box.Shape.findSubShape(e)[1] for e in box.Shape.Edges
             if any(v.isSame(corner) for v in e.Vertexes)]
    fillet = body.newObject("PartDesign::Fillet", "Fillet")
    fillet.Base = (box, edges)
    fillet.Radius = 1
    fillet.Corners = {vname: (2, {edges[0]: 3})}
    doc.recompute()
    Gui.ActiveDocument.setEdit(fillet)
    wait(1)
    tree = [t for t in mw.findChildren(QtWidgets.QTreeWidget, "treeWidgetReferences")
            if t.isVisible()][0]
    row = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())
           if tree.topLevelItem(i).text(0) == vname][0]
    tree.setCurrentItem(row.child(0))
    # wide enough for the Setback column
    docks = [d for d in mw.findChildren(QtWidgets.QDockWidget)
             if d.isVisible() and d.findChild(QtWidgets.QTreeWidget, "treeWidgetReferences")]
    if docks:
        mw.resizeDocks(docks, [560], QtCore.Qt.Horizontal)
    wait(0.5)
    for c in range(tree.columnCount()):
        tree.resizeColumnToContents(c)
    view = Gui.ActiveDocument.ActiveView
    # framed on the corner, from the side the handles point to
    rot = _look((1, 0.75, 0.9))
    view.setCameraOrientation(rot)
    view.fitAll()
    cam = view.getCameraNode()
    pos = V(8.4, 8.4, 8.4) + rot.multVec(V(0, 0, 1)) * 100
    cam.position.setValue(pos.x, pos.y, pos.z)
    cam.height.setValue(9)
    wait(1.5)
    # A window grab leaves the 3D view blank: render it on its own and
    # paint it in where the viewer sits
    pix = mw.grab()
    viewer = view.graphicsView()
    at = viewer.mapTo(mw, QtCore.QPoint(0, 0))
    ratio = pix.devicePixelRatio()
    tmp = os.environ["SHOT"] + ".view.png"
    view.saveImage(tmp, int(viewer.width() * ratio), int(viewer.height() * ratio), "Current")
    from PySide import QtGui
    painter = QtGui.QPainter(pix)
    painter.drawImage(QtCore.QRect(at, viewer.size()), QtGui.QImage(tmp))
    painter.end()
    os.remove(tmp)
    # down to the view's tab bar: the report view below is not the panel's
    bottom = at.y() + viewer.height() + 22
    pix.copy(QtCore.QRect(0, 0, int(pix.width() / ratio), bottom)).save(os.environ["SHOT"])
    emit("SHOT " + os.environ["SHOT"])
    emit("DONE")
    os._exit(0)


def run():
    try:
        shot()
    finally:
        # an error is in the log; never leave the GUI running
        os._exit(0)


QtCore.QTimer.singleShot(1500, run)
