// euse a.brep: edges not used once each way round by the faces (as the pictures' red marks)
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopAbs.hxx>
#include <cstdio>
int main(int, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  TopTools_IndexedMapOfShape em; TopExp::MapShapes(s, TopAbs_EDGE, em);
  for (int i = 1; i <= em.Extent(); ++i)
  {
    int f = 0, r = 0, faces = 0;
    for (TopExp_Explorer xf(s, TopAbs_FACE); xf.More(); xf.Next())
    {
      bool in = false;
      for (TopExp_Explorer xe(xf.Current(), TopAbs_EDGE); xe.More(); xe.Next())
        if (xe.Current().IsSame(em(i)))
        {
          if (in) break; // as render.py: each edge once per face, a seam both ways
          in = true;
          TopAbs_Orientation o = xe.Current().Orientation();
          if (BRep_Tool::IsClosed(TopoDS::Edge(xe.Current()), TopoDS::Face(xf.Current()))) { ++f; ++r; }
          else if (o == TopAbs_FORWARD) ++f; else if (o == TopAbs_REVERSED) ++r;
        }
      faces += in;
    }
    TopoDS_Vertex a, b; TopExp::Vertices(TopoDS::Edge(em(i)), a, b);
    if (!(f == 1 && r == 1) && !BRep_Tool::Degenerated(TopoDS::Edge(em(i))))
    {
      gp_Pnt p = a.IsNull() ? gp_Pnt() : BRep_Tool::Pnt(a), q = b.IsNull() ? gp_Pnt() : BRep_Tool::Pnt(b);
      printf("edge %d fwd %d rev %d faces %d (%.2f %.2f %.2f)-(%.2f %.2f %.2f)\n", i, f, r, faces, p.X(), p.Y(), p.Z(), q.X(), q.Y(), q.Z());
    }
  }
}
