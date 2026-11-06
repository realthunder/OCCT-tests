// sinfo a.brep faceidx: the face's surface -- type, bounds, periodicity, and a B-spline's degrees, knots and rationality
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <Geom_BSplineSurface.hxx>
#include <Geom_OffsetSurface.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cstdio>
#include <cstdlib>
static void info(const occ::handle<Geom_Surface>& s, const char* ind)
{
  double u1, u2, v1, v2; s->Bounds(u1, u2, v1, v2);
  printf("%s%s u [%.10g %.10g] v [%.10g %.10g] uper %d vper %d uclosed %d vclosed %d\n", ind, s->DynamicType()->Name(), u1, u2, v1, v2,
         s->IsUPeriodic(), s->IsVPeriodic(), s->IsUClosed(), s->IsVClosed());
  if (auto b = occ::down_cast<Geom_BSplineSurface>(s)) {
    printf("%s deg %d %d poles %d x %d rational %d %d\n", ind, b->UDegree(), b->VDegree(), b->NbUPoles(), b->NbVPoles(), b->IsURational(), b->IsVRational());
    printf("%s vknots:", ind); for (int i = 1; i <= b->NbVKnots(); ++i) printf(" %.8g(%d)", b->VKnot(i), b->VMultiplicity(i)); printf("\n");
  }
  if (auto o = occ::down_cast<Geom_OffsetSurface>(s)) { printf("%s offset %g of:\n", ind, o->Offset()); info(o->BasisSurface(), "   "); }
}
int main(int argc, char** argv)
{
  BRep_Builder bb; TopoDS_Shape a; BRepTools::Read(a, argv[1], bb);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(a, TopAbs_FACE, fm);
  TopoDS_Face f = TopoDS::Face(fm(atoi(argv[2])));
  double u1, u2, v1, v2; BRepTools::UVBounds(f, u1, u2, v1, v2);
  printf("face uv [%.10g %.10g] [%.10g %.10g] or %d\n", u1, u2, v1, v2, (int)f.Orientation());
  info(BRep_Tool::Surface(f), "");
}
