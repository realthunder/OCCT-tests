// vuse <brep> <vertex idx 1-based ...>: the faces and edges each vertex is on, with tolerance
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Vertex.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  TopTools_IndexedMapOfShape f, e, v; TopExp::MapShapes(s, TopAbs_FACE, f); TopExp::MapShapes(s, TopAbs_EDGE, e); TopExp::MapShapes(s, TopAbs_VERTEX, v);
  TopTools_IndexedDataMapOfShapeListOfShape ve, ef; TopExp::MapShapesAndAncestors(s, TopAbs_VERTEX, TopAbs_EDGE, ve); TopExp::MapShapesAndAncestors(s, TopAbs_EDGE, TopAbs_FACE, ef);
  for (int i = 2; i < argc; ++i) {
    const TopoDS_Vertex& V = TopoDS::Vertex(v(atoi(argv[i])));
    gp_Pnt p = BRep_Tool::Pnt(V);
    printf("v%s (%.4f %.4f %.4f) tol %.3g\n", argv[i], p.X(), p.Y(), p.Z(), BRep_Tool::Tolerance(V));
    TopTools_IndexedMapOfShape seen;
    for (TopTools_ListOfShape::Iterator it(ve.FindFromKey(V)); it.More(); it.Next()) {
      if (seen.Add(it.Value()) == 0) continue;
      const TopoDS_Edge& E = TopoDS::Edge(it.Value());
      TopoDS_Vertex a, b; TopExp::Vertices(E, a, b);
      printf("  e%d v%d-v%d faces", e.FindIndex(E), v.FindIndex(a), v.FindIndex(b));
      TopTools_IndexedMapOfShape fs; for (TopTools_ListOfShape::Iterator jt(ef.FindFromKey(E)); jt.More(); jt.Next()) fs.Add(jt.Value());
      for (int k = 1; k <= fs.Extent(); ++k) printf(" %d", f.FindIndex(fs(k)));
      printf("\n");
    }
  }
}
