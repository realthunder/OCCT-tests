// dome_cap_removed: a box under a B-spline dome, the dome's four edges
// filleted (r 3), and a thickness of it inward with the dome removed (the
// Arc join). See ../README.md, "A filleted dome, the dome removed".
//
// The dome meets each fillet tangentially, 2e-6 rad off, so each of its
// edges is closed by a tube round it (BRepOffset_MakeOffset::ToContext).
// The edges were never taken as tangent -- the test was the angular
// precision, not the angle the analysis works to -- and the result came back
// unhollowed (BRepOffset_UnknownError). Taken as tangent, the tube's edge on
// the dome had no pcurve (its projection onto the dome failed) and stopped
// short of the dome's next edge at each corner, the curve between two tubes
// ended on the one tube's edge to 7e-6 and was not cut by it, and at the
// corner it ended up to 1e-3 off the vertex the tubes start from. Each of
// these is mended (README.md); 1, 2 and 2.5 inward come out valid, to the
// volume of the rule the tube follows, worked numerically: the input less
// the points more than the thickness from every face kept (the input shrunk,
// and the channel under the dome away from its edges).
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade dome_cap_removed.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKOffset -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o dome_cap_removed
// Run: ./dome_cap_removed ../../boolean/models/dome_fillet_r3.brep [--write <dir>]
//   (exit 0 when every run passes)
//   --write: each result, <dir>/in<d>.brep (none when it is refused)
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

int main(int argc, char** argv)
{
    if (argc < 2) {
        printf("usage: %s dome_fillet_r3.brep [--write <dir>]\n", argv[0]);
        return 2;
    }
    const char*  dir = argc > 3 && !strcmp(argv[2], "--write") ? argv[3] : nullptr;
    TopoDS_Shape s;
    BRep_Builder b;
    if (!BRepTools::Read(s, argv[1], b)) {
        printf("cannot read %s\n", argv[1]);
        return 2;
    }
    TopTools_IndexedMapOfShape faces;
    TopExp::MapShapes(s, TopAbs_FACE, faces);
    int bad = 0;
    // the dome (face 9) removed; the volumes worked numerically (to about 1e-5),
    // checked to 1e-4
    struct Run {
        double offset, want;
    } runs[] = {{-1., 10903.5721}, {-2., 21141.2680}, {-2.5, 26016.1606}};
    for (const Run& r : runs) {
        std::string  what;
        bool         ok = false;
        TopoDS_Shape result;
        try {
            NCollection_List<TopoDS_Shape> removed;
            removed.Append(faces(9));
            BRepOffsetAPI_MakeThickSolid m;
            m.MakeThickSolidByJoin(s, removed, r.offset, 1e-7, BRepOffset_Skin, false, false,
                                   GeomAbs_Arc);
            if (!m.IsDone()) {
                what = "refused";
            } else {
                result = m.Shape();
                GProp_GProps g;
                BRepGProp::VolumeProperties(result, g);
                const bool valid = BRepCheck_Analyzer(result).IsValid();
                char       buf[128];
                snprintf(buf, sizeof(buf), "%s, volume %.4f (want %.4f)",
                         valid ? "valid" : "invalid", g.Mass(), r.want);
                what = buf;
                ok   = valid && std::abs(g.Mass() - r.want) <= 1e-4 * r.want;
            }
        } catch (Standard_Failure& e) {
            what = std::string("threw ") + e.what();
        }
        printf("%g %s %s\n", r.offset, ok ? "ok " : "BAD", what.c_str());
        bad += !ok;
        if (dir && !result.IsNull()) {
            char name[64];
            snprintf(name, sizeof(name), "/in%g.brep", -r.offset);
            BRepTools::Write(result, (std::string(dir) + name).c_str());
        }
    }
    printf("%d bad\n", bad);
    return bad != 0;
}
