#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Standard_Failure.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepBuilderAPI_Copy.hxx>
#include <TopTools.hxx>
#include <Bnd_Box.hxx>
#include <BRepBndLib.hxx>
#include <cstring>
#include <string>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <typeinfo>
#include <BRep_Tool.hxx>
#include <TopoDS.hxx>
static int nShow = 0;
static bool showHook(const char* Key, int line, const TopoDS_Shape& s, const char* name)
{
  if (Key) { // an item of a list comes with no key: it goes with the shape before it
    const char* base = strrchr(Key, '/'); base = base ? base + 1 : Key;
    const std::string keys = std::string(" ") + getenv("SHOWKEYS") + " ";
    if (keys.find(std::string(" ") + base + " ") == std::string::npos) return false;
  }
  ++nShow;
  if (s.IsNull()) { printf("%4d %-24s null\n", nShow, name); return true; }
  TopTools_IndexedMapOfShape f, e; TopExp::MapShapes(s, TopAbs_FACE, f); TopExp::MapShapes(s, TopAbs_EDGE, e);
  Bnd_Box b; try { BRepBndLib::Add(s, b); } catch (...) { b.SetVoid(); printf("     (no box)\n"); } double x0 = 0, y0 = 0, z0 = 0, x1 = 0, y1 = 0, z1 = 0; if (!b.IsVoid()) b.Get(x0, y0, z0, x1, y1, z1);
  static const char* T[] = {"Compound", "CompSolid", "Solid", "Shell", "Face", "Wire", "Edge", "Vertex", "Shape"};
  printf("%4d %-24s %-8s f%d e%d (%.2f %.2f %.2f)-(%.2f %.2f %.2f) L%d\n", nShow, name, T[s.ShapeType()], f.Extent(), e.Extent(), x0, y0, z0, x1, y1, z1, line);
  { TopTools_IndexedMapOfShape ee; TopExp::MapShapes(s, TopAbs_EDGE, ee); if (ee.Extent() <= 30) for (int i = 1; i <= ee.Extent(); i++) { TopoDS_Vertex a, b; TopExp::Vertices(TopoDS::Edge(ee(i)), a, b); if (a.IsNull() || b.IsNull()) continue; gp_Pnt pa = BRep_Tool::Pnt(a), pb = BRep_Tool::Pnt(b); printf("       E%p V%p(%.2f %.2f %.2f) V%p(%.2f %.2f %.2f)\n", (void*)ee(i).TShape().get(), (void*)a.TShape().get(), pa.X(), pa.Y(), pa.Z(), (void*)b.TShape().get(), pb.X(), pb.Y(), pb.Z()); } }
  if (getenv("SHOWSAVE")) { char fn[512]; snprintf(fn, sizeof(fn), "%s/%04d_%s.brep", getenv("SHOWSAVE"), nShow, name); BRepTools::Write(s, fn); }
  return true;
}
#include <TopTools_ListOfShape.hxx>
// thkm in.brep offset join(0 arc,1 int) inter faces(1-based, comma list) [OUT=] -- the thickness with the faces removed, SHOWKEYS dumps
int main(int argc, char** argv)
{
  if (getenv("SHOWKEYS")) { setvbuf(stdout, nullptr, _IONBF, 0); SetFuncShowTopoShape(showHook); }
  TopoDS_Shape s; BRep_Builder B; BRepTools::Read(s, argv[1], B);
  double off = atof(argv[2]); GeomAbs_JoinType j = atoi(argv[3]) ? GeomAbs_Intersection : GeomAbs_Arc; bool inter = atoi(argv[4]);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  TopTools_ListOfShape rm; for (char* p = strtok(argv[5], ","); p; p = strtok(nullptr, ",")) rm.Append(fm(atoi(p)));
  try {
    BRepOffsetAPI_MakeThickSolid m; m.MakeThickSolidByJoin(s, rm, off, 1e-7, BRepOffset_Skin, inter, false, j);
    if (!m.IsDone()) { printf("not done\n"); return 1; }
    GProp_GProps g; BRepGProp::VolumeProperties(m.Shape(), g);
    printf("done valid %d vol %.4f\n", BRepCheck_Analyzer(m.Shape()).IsValid(), g.Mass());
    if (getenv("OUT")) BRepTools::Write(m.Shape(), getenv("OUT"));
  } catch (Standard_Failure& e) { printf("threw %s: %s\n", typeid(e).name(), e.what()); }
}
