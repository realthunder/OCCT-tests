// network_degree.cpp: a network of polynomial curves, spanned by GeomFill_NetworkSurface and by
// GeomFill_Gordon, gives a polynomial surface of the curves' degree.
//
// Before the fork's fix (README.md here) both came back rational and of degree 9 from cubic curves:
// the skins and the reference surface were interpolated in homogeneous form with weights of 1, the
// weights came back 1 only to rounding, Geom_BSplineSurface took them for rational, and the exact
// rational product of the three surfaces made the degree 3 x 3. A network of a rational family keeps
// its rational surface (the duct here).
//
// Build against an OCCT install, and run:
//   c++ -std=c++17 -O1 -I<prefix>/include/opencascade network_degree.cpp -o network_degree \
//       -L<prefix>/lib -lTKernel -lTKMath -lTKG3d -lTKGeomBase -lTKGeomAlgo -Wl,-rpath,<prefix>/lib
//   ./network_degree      # a line per network, exits 1 on a failure
#include <GC_MakeArcOfCircle.hxx>
#include <GeomAPI_Interpolate.hxx>
#include <GeomFill_Gordon.hxx>
#include <GeomFill_NetworkSurface.hxx>
#include <Geom_BSplineCurve.hxx>
#include <Geom_BSplineSurface.hxx>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <functional>
#include <vector>

using Fn = std::function<gp_Pnt(double, double)>;

static int failures = 0;

// Through the points at the given parameters: every curve of a family interpolated at the same
// parameters has the same knots
static occ::handle<Geom_BSplineCurve> interp(const std::vector<gp_Pnt>& pts,
                                             const std::vector<double>& params)
{
  occ::handle<NCollection_HArray1<gp_Pnt>> p = new NCollection_HArray1<gp_Pnt>(1, (int)pts.size());
  occ::handle<NCollection_HArray1<double>> t = new NCollection_HArray1<double>(1, (int)pts.size());
  for (size_t i = 0; i < pts.size(); ++i)
  {
    p->SetValue((int)i + 1, pts[i]);
    t->SetValue((int)i + 1, params[i]);
  }
  GeomAPI_Interpolate it(p, t, false, 1e-9);
  it.Perform();
  return it.Curve();
}

static int maxInteriorMult(const occ::handle<Geom_BSplineSurface>& s)
{
  int m = 0;
  for (int i = 2; i < s->NbUKnots(); ++i)
    m = std::max(m, s->UMultiplicity(i));
  for (int i = 2; i < s->NbVKnots(); ++i)
    m = std::max(m, s->VMultiplicity(i));
  return m;
}

static void expect(const char* name, const occ::handle<Geom_BSplineSurface>& s, bool rational,
                   int degree, int maxMult)
{
  if (s.IsNull())
  {
    printf("FAIL %-36s not built\n", name);
    ++failures;
    return;
  }
  const bool isRational = s->IsURational() || s->IsVRational();
  const bool ok = isRational == rational && s->UDegree() <= degree && s->VDegree() <= degree
                  && maxInteriorMult(s) <= maxMult;
  printf("%s %-36s degree %d/%d, %s, %d x %d poles, interior multiplicity %d\n",
         ok ? "ok  " : "FAIL", name, s->UDegree(), s->VDegree(),
         isRational ? "rational" : "polynomial", s->NbUPoles(), s->NbVPoles(), maxInteriorMult(s));
  failures += ok ? 0 : 1;
}

// GeomFill_NetworkSurface on a compatible network of f: profiles through f(u_j, v_i) at u_j and the
// midpoints, guides likewise, so the two families cross at the shared parameters
static void network(const char* name, const Fn& f, const std::vector<double>& us,
                    const std::vector<double>& vs)
{
  auto params = [](const std::vector<double>& c) {
    std::vector<double> t;
    for (size_t k = 0; k < c.size(); ++k)
    {
      t.push_back(c[k]);
      if (k + 1 < c.size())
        t.push_back((c[k] + c[k + 1]) / 2);
    }
    return t;
  };
  const std::vector<double> tu = params(us), tv = params(vs);
  NCollection_Array1<occ::handle<Geom_BSplineCurve>> P(1, (int)vs.size()), G(1, (int)us.size());
  NCollection_Array1<double>                          aU(1, (int)us.size()), aV(1, (int)vs.size());
  NCollection_Array2<gp_Pnt>                          grid(1, (int)us.size(), 1, (int)vs.size());
  NCollection_Array2<double>                          weights(1, (int)us.size(), 1, (int)vs.size());
  weights.Init(1.0);
  for (size_t i = 0; i < vs.size(); ++i)
  {
    std::vector<gp_Pnt> pts;
    for (double u : tu)
      pts.push_back(f(u, vs[i]));
    P.SetValue((int)i + 1, interp(pts, tu));
    aV.SetValue((int)i + 1, vs[i]);
  }
  for (size_t j = 0; j < us.size(); ++j)
  {
    std::vector<gp_Pnt> pts;
    for (double v : tv)
      pts.push_back(f(us[j], v));
    G.SetValue((int)j + 1, interp(pts, tv));
    aU.SetValue((int)j + 1, us[j]);
    for (size_t i = 0; i < vs.size(); ++i)
      grid.SetValue((int)j + 1, (int)i + 1, f(us[j], vs[i]));
  }
  GeomFill_NetworkSurface n;
  n.Init(P, G, aV, aU, grid, weights, 1e-6, false, false);
  n.Perform();
  expect(name, n.IsDone() ? n.Surface() : nullptr, false, 3, 1);
}

static void gordon(const char* name, const std::vector<occ::handle<Geom_Curve>>& p,
                   const std::vector<occ::handle<Geom_Curve>>& g, bool rational, int degree)
{
  NCollection_Array1<occ::handle<Geom_Curve>> P(1, (int)p.size()), G(1, (int)g.size());
  for (size_t i = 0; i < p.size(); ++i)
    P.SetValue((int)i + 1, p[i]);
  for (size_t i = 0; i < g.size(); ++i)
    G.SetValue((int)i + 1, g[i]);
  GeomFill_Gordon gd;
  gd.Init(P, G, 1e-4);
  gd.Perform();
  // Gordon's exact reparametrization puts a knot of full multiplicity at each crossing
  expect(name, gd.IsDone() ? gd.Surface() : nullptr, rational, degree, degree);
}

int main()
{
  const Fn wave = [](double u, double v) {
    double x = 20 * u, y = 12 * v;
    return gp_Pnt(x, y + 1.5 * std::sin(u * 3), 2 * std::sin(x / 4) * std::cos(y / 5));
  };
  network("NetworkSurface, wave 4 x 5", wave, {0, 0.35, 0.7, 1}, {0, 0.3, 0.55, 0.8, 1});

  // through Gordon, the network of scripts/occt-gordon-probe.cpp in FreeCAD that showed it (degree
  // 9, 217 x 212 poles): curves through the crossings and a different number of points between them
  {
    auto through = [&](bool alongU, double fixed, const std::vector<double>& cross, int extra) {
      std::vector<gp_Pnt> pts;
      for (size_t i = 0; i < cross.size(); ++i)
      {
        pts.push_back(alongU ? wave(cross[i], fixed) : wave(fixed, cross[i]));
        if (i + 1 < cross.size())
          for (int k = 1; k <= extra; ++k)
          {
            double t = cross[i] + (cross[i + 1] - cross[i]) * k / (extra + 1);
            pts.push_back(alongU ? wave(t, fixed) : wave(fixed, t));
          }
      }
      occ::handle<NCollection_HArray1<gp_Pnt>> a =
        new NCollection_HArray1<gp_Pnt>(1, (int)pts.size());
      for (size_t i = 0; i < pts.size(); ++i)
        a->SetValue((int)i + 1, pts[i]);
      GeomAPI_Interpolate it(a, false, 1e-9);
      it.Perform();
      return occ::handle<Geom_Curve>(it.Curve());
    };
    const std::vector<double>              vs = {0, 0.3, 0.55, 0.8, 1}, us = {0, 0.35, 0.7, 1};
    std::vector<occ::handle<Geom_Curve>> p, g;
    int                                    k = 0;
    for (double v : vs)
      p.push_back(through(true, v, us, 1 + (k++ % 3)));
    for (double u : us)
      g.push_back(through(false, u, vs, 1 + (k++ % 2)));
    gordon("Gordon, wave 5 x 4, uneven", p, g, false, 3);
  }

  // a duct of rational arcs keeps its rational surface
  {
    std::vector<occ::handle<Geom_Curve>> p, g;
    auto r = [](double z) { return 3 + 0.15 * z; };
    for (double z : {0.0, 4.0, 8.0, 12.0})
      p.push_back(
        GC_MakeArcOfCircle(gp_Pnt(-r(z), 0, z), gp_Pnt(0, r(z), z), gp_Pnt(r(z), 0, z)).Value());
    for (int j = 0; j < 6; ++j)
    {
      double              a = M_PI - M_PI * j / 5;
      std::vector<gp_Pnt> pts;
      std::vector<double> t;
      for (int k = 0; k <= 6; ++k)
      {
        pts.emplace_back(r(2 * k) * std::cos(a), r(2 * k) * std::sin(a), 2 * k);
        t.push_back(k / 6.0);
      }
      g.push_back(interp(pts, t));
    }
    gordon("Gordon, duct of rational arcs", p, g, true, 9);
  }

  printf("%s\n", failures ? "FAILED" : "all ok");
  return failures ? 1 : 0;
}
