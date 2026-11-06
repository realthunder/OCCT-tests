// thk <brep> <offset> <join 0 arc / 2 intersection> <inter 0/1> <face idx 1-based...>: MakeThickSolidByJoin, Skin
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Standard_Failure.hxx>
#include <chrono>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv)
{
  Standard_Failure::SetDefaultStackTraceLength(40); TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  double off = atof(argv[2]); GeomAbs_JoinType j = atoi(argv[3]) ? GeomAbs_Intersection : GeomAbs_Arc; bool inter = atoi(argv[4]);
  TopTools_IndexedMapOfShape F; TopExp::MapShapes(s, TopAbs_FACE, F);
  NCollection_List<TopoDS_Shape> rm; for (int i = 5; i < argc; i++) rm.Append(F(atoi(argv[i])));
  auto t0 = std::chrono::steady_clock::now();
  try {
    BRepOffsetAPI_MakeThickSolid m; m.MakeThickSolidByJoin(s, rm, off, 1e-3, BRepOffset_Skin, inter, false, j);
    double dt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    if (!m.IsDone()) { printf("not done %.1fs error %d\n", dt, (int)m.MakeOffset().Error()); return 1; }
    GProp_GProps g; BRepGProp::VolumeProperties(m.Shape(), g);
    int ns = 0; for (TopExp_Explorer x(m.Shape(), TopAbs_SOLID); x.More(); x.Next()) ns++;
    printf("done %.1fs valid %d solids %d vol %.4f\n", dt, BRepCheck_Analyzer(m.Shape()).IsValid(), ns, g.Mass());
    if (getenv("OUT")) BRepTools::Write(m.Shape(), getenv("OUT"));
  } catch (Standard_Failure& e) { printf("threw %s\n", e.what()); }
}
