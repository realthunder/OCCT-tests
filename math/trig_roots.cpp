// trig_roots.cpp: math_TrigonometricFunctionRoots against a sampling, and a point's projection on an arc
// of ellipse whose range is below zero.
//
// The equation is a cos^2(x) + 2 b cos(x) sin(x) + c cos(x) + d sin(x) + e = 0 between two bounds.
// Random equations of every form the solver has a branch for (some coefficients zero), with bounds
// anywhere, a lower bound below zero in about half of them: each change of sign of a dense sampling
// between the bounds must have a root of the solver's within a step, and each root of the solver's must
// be a root, within the bounds. Before the fork's fix (fillet/README.md, "The roots of a trigonometric
// equation below zero") a lower bound below zero dropped every root between it and zero.
//
// Build against an OCCT install, and run:
//   c++ -std=c++17 -O1 -I<prefix>/include/opencascade trig_roots.cpp -o trig_roots \
//       -L<prefix>/lib -lTKernel -lTKMath -lTKG3d -lTKGeomBase -lTKGeomAlgo -Wl,-rpath,<prefix>/lib
//   ./trig_roots          # prints the counts, exits 1 on a failure
#include <GeomAPI_ProjectPointOnCurve.hxx>
#include <Geom_Ellipse.hxx>
#include <gp_Ax2.hxx>
#include <math_TrigonometricFunctionRoots.hxx>

#include <cmath>
#include <cstdio>
#include <random>

static double f(const double* k, double x)
{
  const double co = std::cos(x), si = std::sin(x);
  return k[0] * co * co + 2 * k[1] * co * si + k[2] * co + k[3] * si + k[4];
}

int main()
{
  std::mt19937_64                        g(12345);
  std::uniform_real_distribution<double> U(-3, 3), B(-9, 9), W(0.05, 2 * M_PI);
  long nCases = 0, nSignChanges = 0, nMissed = 0, nBadRoots = 0;
  for (int it = 0; it < 200000; it++)
  {
    double k[5];
    for (double& x : k)
      x = U(g);
    switch (it % 8)
    {
      case 1: k[0] = k[4] = 0; break;              // the extrema of a point on an ellipse: b, c, d
      case 2: k[0] = k[1] = k[2] = 0; break;       // d sin + e
      case 3: k[0] = k[1] = k[3] = 0; break;       // c cos + e
      case 4: k[0] = k[1] = 0; break;              // c cos + d sin + e
      case 5: k[0] = k[4] = k[2] = 0; break;       // 2b sin cos + d sin
      case 6: k[0] = k[4] = k[3] = 0; break;       // 2b sin cos + c cos
      default: break;                              // the fourth degree
    }
    double lo = B(g), hi = lo + W(g);
    if (it % 5 == 0)
    {
      lo = -M_PI / 2;
      hi = 0;
    }
    math_TrigonometricFunctionRoots r(k[0], k[1], k[2], k[3], k[4], lo, hi);
    if (!r.IsDone() || r.InfiniteRoots())
      continue;
    nCases++;
    const double scale = std::abs(k[0]) + 2 * std::abs(k[1]) + std::abs(k[2]) + std::abs(k[3]) + std::abs(k[4]);
    for (int j = 1; j <= r.NbSolutions(); j++)
    {
      const double x = r.Value(j);
      if (std::abs(f(k, x)) > 1e-6 * scale || x < lo - 1e-7 || x > hi + 1e-7)
      {
        if (++nBadRoots <= 5)
          printf("not a root within the bounds: form %d [%.6f, %.6f] %.9f f %.3g\n", it % 8, lo, hi, x, f(k, x));
      }
    }
    const int M  = 2000;
    double    px = lo, pf = f(k, lo);
    for (int s = 1; s <= M; s++)
    {
      const double x = lo + (hi - lo) * s / M, fx = f(k, x);
      if ((pf < 0) != (fx < 0))
      {
        nSignChanges++;
        bool found = false;
        for (int j = 1; j <= r.NbSolutions() && !found; j++)
          found = r.Value(j) > px - 1e-3 && r.Value(j) < x + 1e-3;
        if (!found && ++nMissed <= 5)
          printf("a change of sign without a root: form %d [%.6f, %.6f] at %.6f\n", it % 8, lo, hi, x);
      }
      px = x;
      pf = fx;
    }
  }
  // the case found: a point on an arc of ellipse running from -PI/2 to 0 (#474's mitre)
  occ::handle<Geom_Ellipse> el = new Geom_Ellipse(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 0.444280185, 0.3);
  const gp_Pnt              p  = el->Value(-M_PI / 4);
  GeomAPI_ProjectPointOnCurve proj(p, el, -M_PI / 2, 0.);
  const bool projOk = proj.NbPoints() == 1 && proj.LowerDistance() < 1e-9
                      && std::abs(proj.LowerDistanceParameter() + M_PI / 4) < 1e-9;
  printf("equations %ld, changes of sign %ld, missed %ld, roots that are not %ld\n", nCases, nSignChanges, nMissed,
         nBadRoots);
  printf("a point on the arc -PI/2..0 projects on it: %s\n", projOk ? "yes" : "NO");
  return (nMissed || nBadRoots || !projOk) ? 1 : 0;
}
