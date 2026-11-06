// meshvol a.brep [deflection]: volume and area of a fine triangulation (BRepMesh), per face area, and edge lengths
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepMesh_IncrementalMesh.hxx>
#include <Poly_Triangulation.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv)
{
  BRep_Builder bb; TopoDS_Shape a; BRepTools::Read(a, argv[1], bb);
  BRepTools::Clean(a);
  BRepMesh_IncrementalMesh m(a, argc > 2 ? atof(argv[2]) : 1e-3, false, 0.05);
  double V = 0, A = 0; int i = 0;
  for (TopExp_Explorer x(a, TopAbs_FACE); x.More(); x.Next()) {
    const TopoDS_Face& f = TopoDS::Face(x.Current()); TopLoc_Location L;
    occ::handle<Poly_Triangulation> t = BRep_Tool::Triangulation(f, L); if (t.IsNull()) { printf("face %d no mesh\n", ++i); continue; }
    double fa = 0, fv = 0; bool rev = f.Orientation() == TopAbs_REVERSED;
    for (int k = 1; k <= t->NbTriangles(); ++k) {
      int n1, n2, n3; t->Triangle(k).Get(n1, n2, n3); if (rev) std::swap(n2, n3);
      gp_XYZ p1 = t->Node(n1).Transformed(L.Transformation()).XYZ(), p2 = t->Node(n2).Transformed(L.Transformation()).XYZ(), p3 = t->Node(n3).Transformed(L.Transformation()).XYZ();
      fa += 0.5 * ((p2 - p1) ^ (p3 - p1)).Modulus(); fv += p1.Dot(p2 ^ p3) / 6.;
    }
    printf("face %d area %.4f volume part %.4f\n", ++i, fa, fv); A += fa; V += fv;
  }
  printf("mesh volume %.4f area %.4f\n", V, A);
  i = 0;
  for (TopExp_Explorer x(a, TopAbs_EDGE); x.More(); x.Next()) { BRepAdaptor_Curve c(TopoDS::Edge(x.Current()));
    printf("edge %d length %.4f\n", ++i, GCPnts_AbscissaPoint::Length(c)); }
}
