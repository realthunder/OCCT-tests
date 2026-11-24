// Directions and frames written to a BRep file and read back, text and
// binary. See ../README.md, "A direction read back as it was written".
//
// gp_Dir keeps the coordinates it is given only when their square norm is 1
// within gp::Resolution(), so in practice only when it is 1 exactly; any other
// is divided by its norm. A direction made by gp_Dir::Transform() (a rotation,
// a placement) is normalized there, and the result is often unit only to an
// ulp: normalized again, it moves by an ulp. gp_Ax2, gp_Ax3 and gp_Ax22d make
// their X and Y directions again from what they are given, which moves a
// frame a rotation left by an ulp the same way. The readers of
// GeomTools_*Set and BinTools_*Set made a gp_Dir of each direction they read
// and a frame of each conic's and elementary surface's, so the shape read
// back was not the shape written, and what was made of it could differ -- in
// FreeCAD, a section view of a fillet with one edge more in a process that
// had read the file than in the one that wrote it.
//
// The cases: the line FreeCAD found it on, its direction as it was in
// memory; then 1000 rotations of (1, 0, 0) about (1, 2, 3), each the
// direction of a line edge, the frame of a circle edge and of a plane face,
// and the frame of a circle on a plane in its parameter space (a pcurve).
// Each shape is written and read back, as BRepTools::Write/Read and as
// BinTools::Write/Read, and every direction compared bit for bit: a case
// passes when every one comes back as it was written.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade brep_direction_round_trip.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKTopAlgo -lTKBRep -lTKGeomBase -lTKG3d -lTKG2d \
//     -lTKMath -lTKernel -o brep_direction_round_trip
// Run: ./brep_direction_round_trip   (exit 0 when every case passes)
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BinTools.hxx>
#include <Geom2d_Circle.hxx>
#include <Geom_Circle.hxx>
#include <Geom_Line.hxx>
#include <Geom_Plane.hxx>
#include <TopExp_Explorer.hxx>
#include <TopLoc_Location.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <gp_Ax22d.hxx>
#include <gp_Circ.hxx>
#include <gp_Circ2d.hxx>
#include <gp_Lin.hxx>
#include <gp_Pln.hxx>
#include <gp_Trsf.hxx>
#include <gp_Trsf2d.hxx>

#include <cstdio>
#include <cstring>
#include <sstream>
#include <vector>

namespace
{

// Every coordinate of the directions of a shape, in the order the explorer
// finds them, of each kind
struct Directions
{
  std::vector<double> lines, circles, planes, circles2d;
};

void add(std::vector<double>& to, const gp_Dir& d)
{
  to.insert(to.end(), {d.X(), d.Y(), d.Z()});
}

void add(std::vector<double>& to, const gp_Dir2d& d)
{
  to.insert(to.end(), {d.X(), d.Y()});
}

Directions directionsOf(const TopoDS_Shape& shape)
{
  Directions res;
  for (TopExp_Explorer ex(shape, TopAbs_EDGE); ex.More(); ex.Next())
  {
    const TopoDS_Edge&      edge  = TopoDS::Edge(ex.Current());
    double                  first = 0., last = 0.;
    occ::handle<Geom_Curve> c = BRep_Tool::Curve(edge, first, last);
    if (auto line = occ::down_cast<Geom_Line>(c))
    {
      add(res.lines, line->Lin().Direction());
    }
    else if (auto circle = occ::down_cast<Geom_Circle>(c))
    {
      add(res.circles, circle->Position().Direction());
      add(res.circles, circle->Position().XDirection());
      add(res.circles, circle->Position().YDirection());
    }
    occ::handle<Geom2d_Curve> c2d;
    occ::handle<Geom_Surface> s;
    TopLoc_Location           loc;
    BRep_Tool::CurveOnSurface(edge, c2d, s, loc, first, last);
    if (auto circle = occ::down_cast<Geom2d_Circle>(c2d))
    {
      add(res.circles2d, circle->Position().XDirection());
      add(res.circles2d, circle->Position().YDirection());
    }
  }
  for (TopExp_Explorer ex(shape, TopAbs_FACE); ex.More(); ex.Next())
  {
    occ::handle<Geom_Surface> s = BRep_Tool::Surface(TopoDS::Face(ex.Current()));
    if (auto plane = occ::down_cast<Geom_Plane>(s))
    {
      add(res.planes, plane->Position().Direction());
      add(res.planes, plane->Position().XDirection());
      add(res.planes, plane->Position().YDirection());
    }
  }
  return res;
}

// How many of the coordinates differ, -1 for another count
int differ(const std::vector<double>& a, const std::vector<double>& b)
{
  if (a.size() != b.size())
  {
    return -1;
  }
  int n = 0;
  for (size_t i = 0; i < a.size(); ++i)
  {
    n += a[i] == b[i] ? 0 : 1;
  }
  return n;
}

TopoDS_Shape throughText(const TopoDS_Shape& shape)
{
  std::stringstream text;
  BRepTools::Write(shape, text);
  TopoDS_Shape back;
  BRep_Builder builder;
  BRepTools::Read(back, text, builder);
  return back;
}

TopoDS_Shape throughBinary(const TopoDS_Shape& shape)
{
  std::stringstream bin(std::ios::in | std::ios::out | std::ios::binary);
  BinTools::Write(shape, bin);
  TopoDS_Shape back;
  BinTools::Read(back, bin);
  return back;
}

} // namespace

int main()
{
  BRep_Builder builder;

  // FreeCAD's case: one line of scanner.FCStd's Binder008, its direction
  // -1.1e-16 off unit in its square norm. gp_Dir's constructor would normalize
  // it, so the bits are put in as they were in memory.
  TopoDS_Compound found;
  builder.MakeCompound(found);
  {
    const double xyz[3] = {-0.70710678118654735, 0.70710678118654757, 0.};
    gp_Dir       d;
    std::memcpy(static_cast<void*>(&d), xyz, sizeof(xyz));
    std::printf("Binder008's line: (%.17g, %.17g, %.17g), norm^2 - 1 = %.3g\n",
                d.X(),
                d.Y(),
                d.Z(),
                d.X() * d.X() + d.Y() * d.Y() + d.Z() * d.Z() - 1.);
    builder.Add(found, BRepBuilderAPI_MakeEdge(gp_Lin(gp_Pnt(7.5, -7.5, 0.), d), 0., 1.).Edge());
  }

  // The sweep
  TopoDS_Compound swept;
  builder.MakeCompound(swept);
  int                             offUnit = 0;
  const gp_Ax1                    axis(gp_Pnt(0., 0., 0.), gp_Dir(1., 2., 3.));
  const occ::handle<Geom_Surface> xy = new Geom_Plane(gp_Pln());
  for (int i = 0; i < 1000; ++i)
  {
    gp_Trsf rot;
    rot.SetRotation(axis, 0.0063 * i);
    gp_Dir d(1., 0., 0.);
    d.Transform(rot);
    offUnit += d.X() * d.X() + d.Y() * d.Y() + d.Z() * d.Z() != 1.0 ? 1 : 0;
    gp_Pnt p(i, 0., 0.);
    builder.Add(swept, BRepBuilderAPI_MakeEdge(gp_Lin(p, d), 0., 1.).Edge());
    gp_Ax2 ax2(p, gp_Dir(0., 0., 1.), gp_Dir(1., 0., 0.));
    ax2.Transform(rot);
    builder.Add(swept, BRepBuilderAPI_MakeEdge(gp_Circ(ax2, 1.)).Edge());
    gp_Ax3 ax3(p, gp_Dir(0., 0., 1.), gp_Dir(1., 0., 0.));
    ax3.Transform(rot);
    builder.Add(swept, BRepBuilderAPI_MakeFace(gp_Pln(ax3), 0., 1., 0., 1.).Face());
    gp_Trsf2d rot2d;
    rot2d.SetRotation(gp_Pnt2d(0., 0.), 0.0063 * i);
    gp_Ax22d ax22d(gp_Pnt2d(i, 0.), gp_Dir2d(1., 0.), gp_Dir2d(0., 1.));
    ax22d.Transform(rot2d);
    occ::handle<Geom2d_Curve> c2d = new Geom2d_Circle(gp_Circ2d(ax22d, 1.));
    builder.Add(swept, BRepBuilderAPI_MakeEdge(c2d, xy).Edge());
  }
  std::printf("sweep: 1000 rotations, %d line directions not unit to the last bit\n", offUnit);

  struct Case
  {
    const char*  name;
    TopoDS_Shape shape;
  };
  int failed = 0;
  for (const Case& c : {Case {"Binder008's line", found}, Case {"sweep", swept}})
  {
    const Directions before = directionsOf(c.shape);
    for (int binary = 0; binary < 2; ++binary)
    {
      const Directions after = directionsOf(binary ? throughBinary(c.shape) : throughText(c.shape));
      const int        lines = differ(before.lines, after.lines);
      const int        circles   = differ(before.circles, after.circles);
      const int        planes    = differ(before.planes, after.planes);
      const int        circles2d = differ(before.circles2d, after.circles2d);
      const bool       ok        = lines == 0 && circles == 0 && planes == 0 && circles2d == 0;
      std::printf("%-16s %-6s: coordinates that differ: lines %d of %zu, circles %d of %zu, "
                  "planes %d of %zu, 2D circles %d of %zu -- %s\n",
                  c.name,
                  binary ? "binary" : "text",
                  lines,
                  before.lines.size(),
                  circles,
                  before.circles.size(),
                  planes,
                  before.planes.size(),
                  circles2d,
                  before.circles2d.size(),
                  ok ? "ok" : "FAIL");
      failed += ok ? 0 : 1;
    }
  }
  std::printf("%s\n", failed ? "FAILED" : "every direction read back as written");
  return failed ? 1 : 0;
}
