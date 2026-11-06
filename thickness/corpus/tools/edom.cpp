// edom <brep> <face idx>: the face's surface domain and each edge's range against its curve's domain
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <Geom_Curve.hxx>
#include <Geom_Surface.hxx>
#include <Geom_TrimmedCurve.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  const TopoDS_Face& F = TopoDS::Face(fm(atoi(argv[2])));
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(F); double u1,u2,v1,v2; S->Bounds(u1,u2,v1,v2);
  double fu1,fu2,fv1,fv2; BRepTools::UVBounds(F,fu1,fu2,fv1,fv2);
  printf("surface %s domain [%g %g]x[%g %g], face [%g %g]x[%g %g]\n", S->DynamicType()->Name(), u1,u2,v1,v2, fu1,fu2,fv1,fv2);
  for (TopExp_Explorer e(F, TopAbs_EDGE); e.More(); e.Next()) {
    double f,l; occ::handle<Geom_Curve> c = BRep_Tool::Curve(TopoDS::Edge(e.Current()), f, l);
    occ::handle<Geom_Curve> b = c; while (!occ::down_cast<Geom_TrimmedCurve>(b).IsNull()) b = occ::down_cast<Geom_TrimmedCurve>(b)->BasisCurve();
    printf("  edge %s (basis %s) range [%g %g] curve [%g %g]\n", c->DynamicType()->Name(), b->DynamicType()->Name(), f, l, c->FirstParameter(), c->LastParameter());
  }
}
