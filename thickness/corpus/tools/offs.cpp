#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <Standard_Failure.hxx>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <typeinfo>
// offs in.brep offset join(0 arc,1 int) inter [OUT=]
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  double off = atof(argv[2]); GeomAbs_JoinType j = atoi(argv[3]) ? GeomAbs_Intersection : GeomAbs_Arc; bool inter = atoi(argv[4]);
  auto t0 = std::chrono::steady_clock::now();
  try {
    BRepOffsetAPI_MakeOffsetShape m; m.PerformByJoin(s, off, getenv("TOL") ? atof(getenv("TOL")) : 1e-7, BRepOffset_Skin, inter, false, j);
    double dt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    if (!m.IsDone()) { printf("not done %.1fs (error %d)\n", dt, (int)m.MakeOffset().Error()); return 1; }
    GProp_GProps g; BRepGProp::SurfaceProperties(m.Shape(), g);
    int nf = 0; for (TopExp_Explorer x(m.Shape(), TopAbs_FACE); x.More(); x.Next()) nf++;
    printf("done %.1fs valid %d faces %d area %.4f\n", dt, BRepCheck_Analyzer(m.Shape()).IsValid(), nf, g.Mass());
    if (getenv("OUT")) BRepTools::Write(m.Shape(), getenv("OUT"));
  } catch (Standard_Failure& e) { printf("threw %s: %s\n", typeid(e).name(), e.what()); }
}
