// dome_crease_fades: a box under a B-spline dome, the dome's four edges
// filleted (r 3), and a thickness of it outward with the bottom removed (the
// Arc join). See ../README.md, "A filleted dome, outward".
//
// At each corner of the dome two fillets meet in a mitre, a crease, and both
// meet the dome tangentially: the crease fades out at the dome's corner. The
// Arc join puts a tube on the crease, of the angle between the faces, which
// closes to nothing there. Its end is degenerated only if the two fillets'
// offsets share the vertex at the corner, and they did not: each made its
// own, 1.8e-6 apart (the faces 1 to 2e-6 rad off tangent at it), as a vertex
// was shared only where every edge at it is tangential. The tube ended in
// an edge of no length that nothing else shared, and the offset shell was
// dropped -- refused (BRepOffset_UnknownError). Now the offset faces share a
// vertex wherever their offsets of it lie within its tolerance of each other.
// Runs: 1, 2 and 3 outward, valid, to the volume booleans give: the part above
// z = 0 of the offset of the shape carried down to z = -10, less the shape.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade dome_crease_fades.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKOffset -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o dome_crease_fades
// Run: ./dome_crease_fades ../../boolean/models/dome_fillet_r3.brep [--write <dir>]
//   (exit 0 when every run passes)
//   --write: each result, <dir>/out<d>.brep (none when it is refused)
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
    // the bottom (face 4) removed; the volumes booleans give
    struct Run {
        double offset, want;
    } runs[] = {{1., 10990.0527}, {2., 22546.8191}, {3., 34682.8715}};
    for (const Run& r : runs) {
        std::string  what;
        bool         ok = false;
        TopoDS_Shape result;
        try {
            NCollection_List<TopoDS_Shape> removed;
            removed.Append(faces(4));
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
                ok   = valid && std::abs(g.Mass() - r.want) <= 1e-6 * r.want;
            }
        } catch (Standard_Failure& e) {
            what = std::string("threw ") + e.what();
        }
        printf("+%g %s %s\n", r.offset, ok ? "ok " : "BAD", what.c_str());
        bad += !ok;
        if (dir && !result.IsNull()) {
            char name[64];
            snprintf(name, sizeof(name), "/out%g.brep", r.offset);
            BRepTools::Write(result, (std::string(dir) + name).c_str());
        }
    }
    printf("%d bad\n", bad);
    return bad != 0;
}
