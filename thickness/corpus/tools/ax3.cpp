// ax3 <brep>: each face's elementary surface, its Ax3 direct or not, the face orientation, BRepCheck
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <Geom_ElementarySurface.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  printf("valid %d\n", BRepCheck_Analyzer(s).IsValid());
  TopTools_IndexedMapOfShape F; TopExp::MapShapes(s, TopAbs_FACE, F);
  for (int i = 1; i <= F.Extent(); i++) {
    TopLoc_Location L; auto su = BRep_Tool::Surface(TopoDS::Face(F(i)), L);
    auto e = occ::down_cast<Geom_ElementarySurface>(su);
    printf("%d %s direct %d ori %d loc %d\n", i, su->DynamicType()->Name(), e ? (int)e->Position().Direct() : -1, (int)F(i).Orientation(), !L.IsIdentity());
  }
}
