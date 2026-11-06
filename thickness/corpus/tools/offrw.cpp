// offrw in.brep off join(0 arc,1 int): validity in memory, then after a write and read back; each curve rep of every edge on a closed face
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRep_TEdge.hxx>
#include <BRep_CurveRepresentation.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <sstream>
#include <cstdio>
#include <cstdlib>
static void reps(const TopoDS_Shape& a)
{
  TopTools_IndexedMapOfShape em; TopExp::MapShapes(a, TopAbs_EDGE, em);
  for (int i = 1; i <= em.Extent(); ++i) {
    occ::handle<BRep_TEdge> te = occ::down_cast<BRep_TEdge>(em(i).TShape());
    printf(" e%d:", i);
    for (auto it = te->Curves().cbegin(); it != te->Curves().cend(); ++it) printf(" %s", (*it)->DynamicType()->Name());
    printf("\n");
  }
}
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  BRepOffsetAPI_MakeOffsetShape m; m.PerformByJoin(s, atof(argv[2]), 1e-7, BRepOffset_Skin, false, false, atoi(argv[3]) ? GeomAbs_Intersection : GeomAbs_Arc);
  TopoDS_Shape r = m.Shape();
  printf("memory valid %d\n", (int)BRepCheck_Analyzer(r).IsValid()); reps(r);
  std::stringstream ss; BRepTools::Write(r, ss); TopoDS_Shape r2; BRepTools::Read(r2, ss, B);
  printf("readback valid %d\n", (int)BRepCheck_Analyzer(r2).IsValid()); reps(r2);
}
