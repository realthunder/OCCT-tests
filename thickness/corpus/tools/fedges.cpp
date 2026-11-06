// fedges <brep> <face idx 1-based ...>: each face's surface and its edges (curve type, ends, degenerated)
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <cstdio>
#include <cstdlib>
static const char* ctype(GeomAbs_CurveType t) { const char* n[] = {"line","circle","ellipse","hyperbola","parabola","bezier","bspline","offset","other"}; return n[t]; }
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  TopTools_IndexedMapOfShape fm, em; TopExp::MapShapes(s, TopAbs_FACE, fm); TopExp::MapShapes(s, TopAbs_EDGE, em);
  for (int a = 2; a < argc; ++a) {
    const TopoDS_Face& f = TopoDS::Face(fm(atoi(argv[a])));
    printf("face %d %s\n", atoi(argv[a]), BRep_Tool::Surface(f)->DynamicType()->Name());
    for (TopExp_Explorer e(f, TopAbs_EDGE); e.More(); e.Next()) {
      const TopoDS_Edge& ed = TopoDS::Edge(e.Current());
      if (BRep_Tool::Degenerated(ed)) { printf("  e%d degenerated\n", em.FindIndex(ed)); continue; }
      BRepAdaptor_Curve c(ed); gp_Pnt p0 = c.Value(c.FirstParameter()), p1 = c.Value(c.LastParameter()), pm = c.Value((c.FirstParameter()+c.LastParameter())/2);
      printf("  e%d %-7s (%.3f %.3f %.3f) (%.3f %.3f %.3f) mid (%.3f %.3f %.3f) tol %.1e\n", em.FindIndex(ed), ctype(c.GetType()), p0.X(), p0.Y(), p0.Z(), p1.X(), p1.Y(), p1.Z(), pm.X(), pm.Y(), pm.Z(), BRep_Tool::Tolerance(ed));
    }
  }
}
