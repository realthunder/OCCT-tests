// loose <brep>: edges whose curve ends are off their vertices by more than 1e-6 (index as TopExp map order)
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cstdio>
int main(int, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  TopTools_IndexedMapOfShape em; TopExp::MapShapes(s, TopAbs_EDGE, em);
  for (int i = 1; i <= em.Extent(); ++i) {
    const TopoDS_Edge& e = TopoDS::Edge(em(i)); if (BRep_Tool::Degenerated(e)) continue;
    TopoDS_Vertex v1, v2; TopExp::Vertices(e, v1, v2); BRepAdaptor_Curve c(e);
    gp_Pnt p1 = c.Value(c.FirstParameter()), p2 = c.Value(c.LastParameter());
    double d1 = p1.Distance(BRep_Tool::Pnt(v1)), d2 = p2.Distance(BRep_Tool::Pnt(v2));
    if (d1 > 1e-6 || d2 > 1e-6) printf("Edge%d %s d1 %.3g (%.4f %.4f %.4f) d2 %.3g (%.4f %.4f %.4f) tol %.2g vtol %.2g %.2g\n", i, c.GetType() == GeomAbs_BSplineCurve ? "bspline" : "other", d1, p1.X(), p1.Y(), p1.Z(), d2, p2.X(), p2.Y(), p2.Z(), BRep_Tool::Tolerance(e), BRep_Tool::Tolerance(v1), BRep_Tool::Tolerance(v2));
  }
}
