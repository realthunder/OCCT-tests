// osculating_threads.cpp: one Geom_OffsetSurface evaluated by several threads at once where its
// normal degenerates and the osculating surfaces stand in for it.
//
// The basis is a spherical cap made a B-spline (GeomConvert), its pole a row of equal poles, so the
// offset surface builds osculating surfaces along it (Geom_OsculatingSurface). Each thread takes its
// own GeomAdaptor_Surface of the one surface and evaluates D1 on the pole row and anywhere else.
// Before the fork's fix (README.md) the osculating surfaces were fetched with
// NCollection_Sequence::Value, const but moving the sequence's own cursor: the threads' cursors
// crossed and the process segfaulted -- as a parallel boolean of #346's shells did in FreeCAD.
//
// Build against an OCCT install, and run:
//   c++ -std=c++17 -O1 -pthread -I<prefix>/include/opencascade osculating_threads.cpp \
//       -o osculating_threads -L<prefix>/lib -lTKernel -lTKMath -lTKG3d -lTKGeomBase \
//       -Wl,-rpath,<prefix>/lib
//   ./osculating_threads   # exits 0, or crashes (before the fix: on every run here, 8 threads)
#include <GeomConvert.hxx>
#include <Geom_BSplineSurface.hxx>
#include <Geom_OffsetSurface.hxx>
#include <Geom_RectangularTrimmedSurface.hxx>
#include <Geom_SphericalSurface.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <gp_Ax3.hxx>

#include <cmath>
#include <cstdio>
#include <thread>
#include <vector>

int main()
{
  occ::handle<Geom_SphericalSurface> aSphere = new Geom_SphericalSurface(gp_Ax3(), 10.);
  occ::handle<Geom_RectangularTrimmedSurface> aCap =
    new Geom_RectangularTrimmedSurface(aSphere, 0., 2. * M_PI, M_PI / 4., M_PI / 2.);
  occ::handle<Geom_BSplineSurface> aBS = GeomConvert::SurfaceToBSplineSurface(aCap);
  occ::handle<Geom_OffsetSurface>  anOff = new Geom_OffsetSurface(aBS, 1.);
  double u1, u2, v1, v2;
  anOff->Bounds(u1, u2, v1, v2);
  const int aNbThreads = 8, aNbIter = 200000;
  std::vector<std::thread> aThreads;
  for (int t = 0; t < aNbThreads; ++t)
  {
    aThreads.emplace_back([&, t]() {
      GeomAdaptor_Surface anAd(anOff);
      unsigned            r = 12345u + 7919u * t;
      for (int i = 0; i < aNbIter; ++i)
      {
        r               = r * 1103515245u + 12345u;
        const double fu = (r >> 8) / 16777216.;
        r               = r * 1103515245u + 12345u;
        const double fv = (r >> 8) / 16777216.;
        const double v  = (i % 2 == 0) ? ((i & 4) ? v1 : v2) : v1 + (v2 - v1) * fv;
        gp_Pnt       aP;
        gp_Vec       aDU, aDV;
        try
        {
          anAd.D1(u1 + (u2 - u1) * fu, v, aP, aDU, aDV);
        }
        catch (...)
        {
        }
      }
    });
  }
  for (std::thread& aT : aThreads)
  {
    aT.join();
  }
  printf("%d threads, %d evaluations each: no crash\n", aNbThreads, aNbIter);
  return 0;
}
