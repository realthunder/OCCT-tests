// A frozen edge given a pcurve on a new surface holds it as a cache. The
// question is put through BRep_Builder_IsCache, a C function of the fork
// looked up by name at run time, as a client that must also load with
// upstream's library has to: with upstream's there is no such function, and
// this says so and passes.
//
//   c++ -std=c++17 -I<include>/opencascade iscache.cpp -L<lib> -lTKernel -lTKMath \
//       -lTKBRep -lTKG2d -lTKG3d -lTKGeomBase -lTKTopAlgo -Wl,-rpath,<lib> -o iscache
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRep_Builder.hxx>
#include <BRep_CurveRepresentation.hxx>
#include <BRep_TEdge.hxx>
#include <Geom2d_Line.hxx>
#include <Geom_Plane.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <gp_Pln.hxx>

#include <cstdio>
#ifdef _WIN32
  #include <windows.h>
#else
  #include <dlfcn.h>
#endif

typedef bool (*IsCacheFunc)(const Standard_Transient*);

static IsCacheFunc lookUpIsCache()
{
#ifdef _WIN32
  HMODULE aModule = GetModuleHandleA("TKBRep.dll");
  return aModule ? (IsCacheFunc)GetProcAddress(aModule, "BRep_Builder_IsCache") : nullptr;
#else
  return (IsCacheFunc)dlsym(RTLD_DEFAULT, "BRep_Builder_IsCache");
#endif
}

int main()
{
  const IsCacheFunc isCache = lookUpIsCache();
  if (isCache == nullptr)
  {
    std::printf("no BRep_Builder_IsCache: upstream's library, nothing to ask\n");
    return 0;
  }
  TopoDS_Edge             e = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(1, 0, 0));
  BRep_Builder            b;
  occ::handle<Geom_Plane> own   = new Geom_Plane(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)));
  occ::handle<Geom_Plane> other = new Geom_Plane(gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)));
  b.UpdateEdge(e, new Geom2d_Line(gp_Pnt2d(0, 0), gp_Dir2d(1, 0)), own, TopLoc_Location(), 1e-7);
  // TopoDS_TShape::Immutable is the fork's as well, an inline of its header:
  // this file is compiled against the fork's headers
  e.TShape()->Immutable(true);
  b.UpdateEdge(e, new Geom2d_Line(gp_Pnt2d(0, 0), gp_Dir2d(1, 0)), other, TopLoc_Location(), 1e-7);
  int own_n = 0, cache_n = 0, n = 0;
  for (const occ::handle<BRep_CurveRepresentation>& cr :
       occ::down_cast<BRep_TEdge>(e.TShape())->Curves())
  {
    n++;
    if (!cr->IsCurveOnSurface())
    {
      continue;
    }
    const bool isC = isCache(cr.get());
    std::printf("pcurve on %s: cache %d, type %s\n", cr->Surface() == own ? "own" : "other",
                (int)isC, cr->DynamicType()->Name());
    (cr->Surface() == own ? own_n : cache_n) += isC ? 1 : 0;
  }
  const bool ok = own_n == 0 && cache_n == 1 && n == 3;
  std::printf("%s (%d representations)\n", ok ? "OK" : "WRONG", n);
  return ok ? 0 : 1;
}
