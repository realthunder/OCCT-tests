// faces <brep>: each solid's faces -- surface type, area, wires, edges
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <BRep_Tool.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  int si = 0;
  for (TopExp_Explorer x(s, TopAbs_SOLID); x.More(); x.Next(), si++) {
    GProp_GProps g; BRepGProp::VolumeProperties(x.Current(), g, 1e-9);
    printf("solid %d vol %.4f\n", si, g.Mass());
    for (TopExp_Explorer f(x.Current(), TopAbs_FACE); f.More(); f.Next()) {
      GProp_GProps a; BRepGProp::SurfaceProperties(f.Current(), a);
      int nw = 0, ne = 0; for (TopExp_Explorer w(f.Current(), TopAbs_WIRE); w.More(); w.Next()) nw++;
      for (TopExp_Explorer e(f.Current(), TopAbs_EDGE); e.More(); e.Next()) ne++;
      double u1, u2, v1, v2; BRepTools::UVBounds(TopoDS::Face(f.Current()), u1, u2, v1, v2);
      printf("  %s area %.4f wires %d edges %d uv [%.4f %.4f]x[%.4f %.4f] tol %.3g\n",
             BRepAdaptor_Surface(TopoDS::Face(f.Current())).GetType() == GeomAbs_Plane ? "plane" : "cyl  ",
             a.Mass(), nw, ne, u1, u2, v1, v2, BRep_Tool::Tolerance(TopoDS::Face(f.Current())));
    }
  }
}
