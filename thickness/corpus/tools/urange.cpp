// urange <brep>: each face's UV bounds to full precision, and 2 pi less its U span
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cmath>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  TopTools_IndexedMapOfShape m; TopExp::MapShapes(s, TopAbs_FACE, m);
  for (int i = 1; i <= m.Extent(); i++) { double u1, u2, v1, v2; BRepTools::UVBounds(TopoDS::Face(m(i)), u1, u2, v1, v2);
    printf("f%d u [%.17g %.17g] free-half %.3g\n", i, u1, u2, (2 * M_PI - (u2 - u1)) - M_PI); }
}
