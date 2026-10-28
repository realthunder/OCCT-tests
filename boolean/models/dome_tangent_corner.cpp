// dome_tangent_corner: a box under a B-spline dome, the dome's four edges
// filleted (r 3), and a thickness of it 2 inward with the bottom removed (the
// Arc join): the offsets of two fillets that meet at a corner of the dome
// must cut each other in an edge, through BOPAlgo_PaveFiller. See
// ../README.md, "A section's tangent end at a corner".
//
// At each corner of the dome two fillets meet in a mitre and both meet the
// dome tangentially, so their offsets are tangent to each other at the
// corner's offset. Their section is a curve that passes the corner at a
// hair's distance (4 to 7e-4), not through it, and leaves the faces across
// the boundary of one, where its end is not on both faces and was given no
// vertex: the section had one end, no edge, and the thickness had nothing to
// cut the fillets' offsets with there -- refused (BRepOffset_UnknownError).
// Now such an end takes the corner's vertex, which lies on both faces.
// Runs: each mitre pair's offsets alone (each face its own vertex at the
// corner) sectioned by BRepAlgoAPI_Section; the thickness (the vertex the
// faces share), to the volume booleans give: the shape less the part above
// z = 0 of the offset of it carried down to z = -10.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade dome_tangent_corner.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKOffset -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o dome_tangent_corner
// Run: ./dome_tangent_corner dome_fillet_r3.brep [--write <dir>]   (exit 0 when every run passes)
//   --write: each pair's faces and section, <dir>/pair<i>x<j>.brep, a compound, and
//   the thickness, <dir>/thickness.brep (none when it is refused)
#include <BRepAlgoAPI_Section.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepLib.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_Offset.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
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
    // the fillets are faces 3, 7, 8 and 10; the mitres 3x8, 3x10, 7x8 and 7x10
    // (the section's length: the run after the fix)
    struct Pair {
        int    f1, f2;
        double length;
    } pairs[] = {{3, 8, 1.7038}, {3, 10, 1.7038}, {7, 8, 1.7038}, {7, 10, 1.7038}};
    for (const Pair& p : pairs) {
        // as BRepOffset_Tool::Inter3D does: the offsets' edges have no 3D curves
        const TopoDS_Face o1 = BRepOffset_Offset(TopoDS::Face(faces(p.f1)), -2.).Face();
        const TopoDS_Face o2 = BRepOffset_Offset(TopoDS::Face(faces(p.f2)), -2.).Face();
        BRepLib::BuildCurves3d(o1);
        BRepLib::BuildCurves3d(o2);
        BRepAlgoAPI_Section section(o1, o2);
        int    edges  = 0;
        double length = 0.;
        for (TopExp_Explorer x(section.Shape(), TopAbs_EDGE); x.More(); x.Next(), edges++) {
            GProp_GProps g;
            BRepGProp::LinearProperties(x.Current(), g);
            length += g.Mass();
        }
        const bool ok = edges == 1 && std::abs(length - p.length) <= 1e-3 * p.length;
        printf("mitre %2dx%-2d %s %d edge(s), length %.4f (want %.4f)\n", p.f1, p.f2,
               ok ? "ok " : "BAD", edges, length, p.length);
        bad += !ok;
        if (dir) {
            TopoDS_Compound c;
            b.MakeCompound(c);
            b.Add(c, o1);
            b.Add(c, o2);
            b.Add(c, section.Shape());
            char name[64];
            snprintf(name, sizeof(name), "/pair%dx%d.brep", p.f1, p.f2);
            BRepTools::Write(c, (std::string(dir) + name).c_str());
        }
    }
    // the thickness, the bottom (face 4) removed
    const double want = 20254.4292;
    std::string  what;
    bool         ok = false;
    TopoDS_Shape result;
    try {
        NCollection_List<TopoDS_Shape> removed;
        removed.Append(faces(4));
        BRepOffsetAPI_MakeThickSolid m;
        m.MakeThickSolidByJoin(s, removed, -2., 1e-7, BRepOffset_Skin, false, false, GeomAbs_Arc);
        if (!m.IsDone()) {
            what = "refused";
        } else {
            result = m.Shape();
            GProp_GProps g;
            BRepGProp::VolumeProperties(result, g);
            const bool valid = BRepCheck_Analyzer(result).IsValid();
            char       buf[128];
            snprintf(buf, sizeof(buf), "%s, volume %.4f (want %.4f)", valid ? "valid" : "invalid",
                     g.Mass(), want);
            what = buf;
            ok   = valid && std::abs(g.Mass() - want) <= 1e-6 * want;
        }
    } catch (Standard_Failure& e) {
        what = std::string("threw ") + e.what();
    }
    printf("thickness   %s %s\n", ok ? "ok " : "BAD", what.c_str());
    bad += !ok;
    if (dir && !result.IsNull())
        BRepTools::Write(result, (std::string(dir) + "/thickness.brep").c_str());
    printf("%d bad\n", bad);
    return bad != 0;
}
