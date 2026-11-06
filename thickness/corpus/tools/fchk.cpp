// fchk a.brep: each face's BRepCheck status (non-OK ones), its surface type, wires, edges and area
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepCheck_Result.hxx>
#include <BRepCheck_ListOfStatus.hxx>
#include <BRepCheck.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <Bnd_Box.hxx>
#include <BRepBndLib.hxx>
#include <cstdio>
#include <iostream>
int main(int argc, char** argv)
{
  BRep_Builder bb; TopoDS_Shape a; BRepTools::Read(a, argv[1], bb);
  BRepCheck_Analyzer an(a);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(a, TopAbs_FACE, fm);
  for (int i = 1; i <= fm.Extent(); ++i) {
    const TopoDS_Face& f = TopoDS::Face(fm(i));
    occ::handle<BRepCheck_Result> r = an.Result(f);
    bool bad = false;
    if (!r.IsNull()) for (auto it = r->Status().cbegin(); it != r->Status().cend(); ++it) if (*it != BRepCheck_NoError) bad = true;
    int nw = 0, ne = 0; for (TopExp_Explorer w(f, TopAbs_WIRE); w.More(); w.Next()) ++nw; for (TopExp_Explorer e(f, TopAbs_EDGE); e.More(); e.Next()) ++ne;
    GProp_GProps g; BRepGProp::SurfaceProperties(f, g); Bnd_Box b; BRepBndLib::Add(f, b); double x0,y0,z0,x1,y1,z1; b.Get(x0,y0,z0,x1,y1,z1);
    printf("face %d type %d wires %d edges %d area %.4f box z %.3f..%.3f%s", i, BRepAdaptor_Surface(f).GetType(), nw, ne, g.Mass(), z0, z1, bad ? " BAD:" : "\n");
    if (bad) { for (auto it = r->Status().cbegin(); it != r->Status().cend(); ++it) { std::cout << " "; BRepCheck::Print(*it, std::cout); } }
  }
}
