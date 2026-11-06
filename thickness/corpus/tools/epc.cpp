// epc e.brep...: each edge's pcurves -- surface type and the pcurve's ends in (u, v)
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_TEdge.hxx>
#include <BRep_CurveRepresentation.hxx>
#include <BRep_GCurve.hxx>
#include <Geom2d_Curve.hxx>
#include <Geom_Surface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  for (int a = 1; a < argc; ++a) {
    BRep_Builder bb; TopoDS_Shape s; BRepTools::Read(s, argv[a], bb);
    for (TopExp_Explorer x(s, TopAbs_EDGE); x.More(); x.Next()) {
      auto te = occ::down_cast<BRep_TEdge>(x.Current().TShape());
      printf("%s or %d\n", argv[a], (int)x.Current().Orientation());
      for (auto it = te->Curves().cbegin(); it != te->Curves().cend(); ++it) {
        auto g = occ::down_cast<BRep_GCurve>(*it);
        if (g.IsNull() || !g->IsCurveOnSurface()) continue;
        double f = g->First(), l = g->Last();
        auto c = g->PCurve(); gp_Pnt2d p = c->Value(f), q = c->Value(l);
        printf("  %s %s (%.4f %.4f)-(%.4f %.4f)", g->Surface()->DynamicType()->Name(), g->IsCurveOnClosedSurface() ? "closed" : "", p.X(), p.Y(), q.X(), q.Y());
        if (g->IsCurveOnClosedSurface()) { auto c2 = g->PCurve2(); p = c2->Value(f); q = c2->Value(l); printf(" | (%.4f %.4f)-(%.4f %.4f)", p.X(), p.Y(), q.X(), q.Y()); }
        printf("\n");
      }
    }
  }
}
