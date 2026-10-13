"""python ifc_serialise.py <shape.brep>

What FreeCAD's IFC export does with a shape: conda-forge's ifcopenshell,
built against upstream OCCT, reads a BRep string through a
BRepTools_ShapeSet it holds itself. Run it with the fork's libraries first
on the loader's path (DYLD_LIBRARY_PATH or LD_LIBRARY_PATH); it crashed
while that class was larger than upstream's (README.md).
"""
import sys

import ifcopenshell
import ifcopenshell.geom

brep = open(sys.argv[1]).read()
for _ in range(3):
    assert ifcopenshell.geom.serialise("IFC4", brep) is not None
    assert ifcopenshell.geom.tesselate("IFC4", brep, 0.1) is not None
print("ifcopenshell", ifcopenshell.version, "serialise and tesselate: ok")
