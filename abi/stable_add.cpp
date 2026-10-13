// The text writer under SetStableBytes, the shape given to upstream's Add(): what the shape does not own is left out.
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepTools_ShapeSet.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <cstdio>
#include <sstream>
#include <string>
static int count(const std::string& s, const char* key)
{
  const size_t i = s.find(key);
  return i == std::string::npos ? -1 : std::atoi(s.c_str() + i + std::strlen(key));
}
static std::string write(const TopoDS_Shape& theS, const bool theStable, const bool theNameFirst)
{
  BRepTools_ShapeSet aSet(false);
  aSet.SetStableBytes(theStable);
  if (theNameFirst) aSet.AddOwnSurfaces(theS);
  aSet.TopTools_ShapeSet::Add(theS);
  std::ostringstream os;
  aSet.Write(os);
  return os.str();
}
int main()
{
  TopoDS_Shape aBox  = BRepPrimAPI_MakeBox(1., 2., 3.).Shape();
  TopoDS_Shape aFace = TopExp_Explorer(aBox, TopAbs_FACE).Current();
  bool ok = true;
  for (int k = 0; k < 2; k++)
  {
    const TopoDS_Shape& aS = k == 0 ? aBox : aFace;
    const std::string plain = write(aS, false, false), stable = write(aS, true, false), named = write(aS, true, true);
    std::printf("%s: plain surfaces %d curve2ds %d | stable %d %d | stable, named first %d %d | same bytes %d\n",
                k == 0 ? "box " : "face", count(plain, "Surfaces "), count(plain, "Curve2ds "),
                count(stable, "Surfaces "), count(stable, "Curve2ds "), count(named, "Surfaces "),
                count(named, "Curve2ds "), (int)(stable == named));
    ok = ok && stable == named;
    if (k == 1) ok = ok && count(stable, "Surfaces ") == 1 && count(plain, "Surfaces ") == 5;
    if (k == 0) ok = ok && count(stable, "Surfaces ") == 6;
  }
  std::printf("%s\n", ok ? "OK" : "WRONG");
  return ok ? 0 : 1;
}
