// fpc2 <brep> <face...>: each edge of the face: pcurve on it (own or computed), BRepCheck_Edge status in the face
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepCheck_Edge.hxx>
#include <BRepCheck_Wire.hxx>
#include <BRepCheck_ListOfStatus.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Geom2d_Curve.hxx>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  TopTools_IndexedMapOfShape F; TopExp::MapShapes(s, TopAbs_FACE, F);
  for (int a = 2; a < argc; a++) {
    TopoDS_Face f = TopoDS::Face(F(atoi(argv[a])));
    printf("face %s ori %d\n", argv[a], (int)f.Orientation());
    for (TopExp_Explorer x(f, TopAbs_EDGE); x.More(); x.Next()) {
      TopoDS_Edge e = TopoDS::Edge(x.Current()); double f0, l0; bool stored = false;
      occ::handle<Geom2d_Curve> pc = BRep_Tool::CurveOnSurface(e, f, f0, l0, &stored);
      BRepCheck_Edge ce(e); ce.InContext(f); int bad = 0;
      for (auto it = ce.StatusOnShape(f).cbegin(); it != ce.StatusOnShape(f).cend(); ++it) if (*it != BRepCheck_NoError) { printf("    status %d\n", (int)*it); bad = 1; }
      gp_Pnt2d p0 = pc.IsNull() ? gp_Pnt2d() : pc->Value(f0), p1 = pc.IsNull() ? gp_Pnt2d() : pc->Value(l0);
      printf("  edge ori %d pc %s stored %d range %g %g uv (%.4f %.4f)-(%.4f %.4f) closed %d\n", (int)e.Orientation(), pc.IsNull() ? "NULL" : "yes", stored, f0, l0, p0.X(), p0.Y(), p1.X(), p1.Y(), BRep_Tool::IsClosed(e, f));
    }
  }
}
