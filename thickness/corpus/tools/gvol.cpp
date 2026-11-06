// gvol a.brep: BRepGProp volume plain, adaptive (eps 1e-6), and each face's area plain/adaptive
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  BRep_Builder bb; TopoDS_Shape a; BRepTools::Read(a, argv[1], bb);
  GProp_GProps g; BRepGProp::VolumeProperties(a, g); GProp_GProps h; double e = BRepGProp::VolumeProperties(a, h, 1e-6);
  printf("volume plain %.4f adaptive %.4f (err %.2g)\n", g.Mass(), h.Mass(), e);
  int i = 0;
  for (TopExp_Explorer x(a, TopAbs_FACE); x.More(); x.Next()) {
    GProp_GProps s, t; BRepGProp::SurfaceProperties(x.Current(), s); BRepGProp::SurfaceProperties(x.Current(), t, 1e-6);
    GProp_GProps v, w; BRepGProp::VolumeProperties(TopoDS::Face(x.Current()), v); BRepGProp::VolumeProperties(TopoDS::Face(x.Current()), w, 1e-6);
    printf("face %d type %d area %.4f / %.4f, volume part %.4f / %.4f\n", ++i, BRepAdaptor_Surface(TopoDS::Face(x.Current())).GetType(), s.Mass(), t.Mass(), v.Mass(), w.Mass());
  }
}
