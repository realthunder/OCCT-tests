// vnear <brep> x y z r: the vertices within r of the point -- index, tolerance, edges on it
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Vertex.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  gp_Pnt q(atof(argv[2]), atof(argv[3]), atof(argv[4])); double r = atof(argv[5]);
  TopTools_IndexedDataMapOfShapeListOfShape ve; TopExp::MapShapesAndAncestors(s, TopAbs_VERTEX, TopAbs_EDGE, ve);
  for (int i = 1; i <= ve.Extent(); ++i) {
    const TopoDS_Vertex& V = TopoDS::Vertex(ve.FindKey(i));
    gp_Pnt p = BRep_Tool::Pnt(V);
    if (p.Distance(q) > r) continue;
    TopTools_IndexedMapOfShape es; for (TopTools_ListOfShape::Iterator it(ve(i)); it.More(); it.Next()) es.Add(it.Value());
    printf("v%d d %.3g tol %.3g edges %d\n", i, p.Distance(q), BRep_Tool::Tolerance(V), es.Extent());
  }
}
