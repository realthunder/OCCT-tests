// vol <brep...>: each solid's volume at eps 1e-9 (adaptive), and the default
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS_Shape.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  for (int i = 1; i < argc; i++) {
    TopoDS_Shape s; BRep_Builder b;
    if (!BRepTools::Read(s, argv[i], b)) { printf("%s: unreadable\n", argv[i]); continue; }
    for (TopExp_Explorer x(s, TopAbs_SOLID); x.More(); x.Next()) {
      GProp_GProps p, q;
      double err = BRepGProp::VolumeProperties(x.Current(), p, 1.e-9);
      BRepGProp::VolumeProperties(x.Current(), q);
      printf("%s: %.6f (err %.1e)  default %.6f\n", argv[i], p.Mass(), err, q.Mass());
    }
  }
}
