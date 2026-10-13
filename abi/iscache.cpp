// A frozen edge given a pcurve on a new surface holds it as a cache, and says so through BRep_Builder::IsCache.
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRep_Builder.hxx>
#include <BRep_TEdge.hxx>
#include <BRep_CurveRepresentation.hxx>
#include <Geom2d_Line.hxx>
#include <Geom_Plane.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <gp_Pln.hxx>
#include <cstdio>
int main()
{
  TopoDS_Edge  e = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(1, 0, 0));
  BRep_Builder b;
  occ::handle<Geom_Plane> own = new Geom_Plane(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)));
  occ::handle<Geom_Plane> other = new Geom_Plane(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)));
  b.UpdateEdge(e, new Geom2d_Line(gp_Pnt2d(0, 0), gp_Dir2d(1, 0)), own, TopLoc_Location(), 1e-7);
  e.TShape()->Immutable(true);
  b.UpdateEdge(e, new Geom2d_Line(gp_Pnt2d(0, 0), gp_Dir2d(1, 0)), other, TopLoc_Location(), 1e-7);
  int own_n = 0, cache_n = 0, n = 0;
  for (const occ::handle<BRep_CurveRepresentation>& cr : occ::down_cast<BRep_TEdge>(e.TShape())->Curves())
  {
    n++;
    if (!cr->IsCurveOnSurface()) continue;
    const bool isC = BRep_Builder::IsCache(cr);
    std::printf("pcurve on %s: cache %d, type %s\n", cr->Surface() == own ? "own" : "other", (int)isC, cr->DynamicType()->Name());
    (cr->Surface() == own ? own_n : cache_n) += isC ? 1 : 0;
  }
  const bool ok = own_n == 0 && cache_n == 1 && n == 3;
  std::printf("%s (%d representations)\n", ok ? "OK" : "WRONG", n);
  return ok ? 0 : 1;
}
