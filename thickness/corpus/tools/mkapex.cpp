// mkapex kind out.brep: cone (r 5 to an apex, h 8), sphere (r 5), spindle (a torus R 2 r 3: its tube crosses the axis)
#include <BRepTools.hxx>
#include <BRepPrimAPI_MakeCone.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepPrimAPI_MakeTorus.hxx>
#include <cstring>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s;
  if (!strcmp(argv[1], "cone")) s = BRepPrimAPI_MakeCone(5, 0, 8).Shape();
  else if (!strcmp(argv[1], "sphere")) s = BRepPrimAPI_MakeSphere(5).Shape();
  else s = BRepPrimAPI_MakeTorus(2, 3).Shape();
  BRepTools::Write(s, argv[2]);
}
