// issue580: a solid whose planar face holds a degenerated edge, transformed
// with a copy -- mirrored, moved and scaled (BRepBuilderAPI_Transform, what
// FreeCAD's mirror, placement copies and scaling run) -- and the mirror
// fused back. See ../README.md, #580.
//
// issue580_pad003.brep is #580's Pad003 (../../occ-issues/models/
// issue580_mirror_crash.FCStd), 700.9305: its face 19, a plane, holds a
// degenerated edge with no 3D curve. Each copy must be valid with the
// volume it should have (the same, or 8 times scaled by 2), and the fuse of
// the solid with its mirror valid, twice the solid less their common.
//
// Until BRepTools_TrsfModification was fixed here, the copy dropped the
// pcurve of any edge on a plane, BRep_Tool projecting the 3D curve when one
// is asked for -- but a degenerated edge has none: it was left with no
// curve at all, the face "NoCurveOnSurface", the solid invalid (the mirror
// 652.3448 by the volume integrals), and FreeCAD's fuse of the mirror with
// the solid invalid too (in 2022 it crashed).
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade issue580_mirror_degenerated.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKBO -lTKTopAlgo -lTKBRep -lTKGeomAlgo -lTKGeomBase \
//     -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue580_mirror_degenerated
// Run: ./issue580_mirror_degenerated issue580_pad003.brep [--write <dir>]
//   (exit 0 when every check passes; --write: the mirror and the fuse,
//   <dir>/mirror.brep and <dir>/fuse.brep, for ../pictures/make_pictures.sh)
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <gp_Ax2.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

static double volume(const TopoDS_Shape& s)
{
    GProp_GProps g;
    BRepGProp::VolumeProperties(s, g, 1.e-9);
    return g.Mass();
}

static int bad = 0;

static void check(const char* what, const TopoDS_Shape& s, double expected)
{
    const bool   valid = BRepCheck_Analyzer(s).IsValid();
    const double v     = volume(s);
    const bool   ok    = valid && (expected <= 0. || std::abs(v - expected) <= 1.e-6 * expected);
    printf("%-22s %s valid %d vol %.4f", what, ok ? "ok " : "BAD", valid, v);
    if (expected > 0.)
        printf(" (want %.4f)", expected);
    printf("\n");
    bad += !ok;
}

int main(int argc, char** argv)
{
    TopoDS_Shape s;
    BRep_Builder b;
    if (argc < 2 || !BRepTools::Read(s, argv[1], b)) {
        printf("usage: %s issue580_pad003.brep [--write <dir>]\n", argv[0]);
        return 2;
    }
    const char* dir = argc > 3 && !strcmp(argv[2], "--write") ? argv[3] : nullptr;
    const double v0 = volume(s);
    check("input", s, v0);

    gp_Trsf mirror;
    mirror.SetMirror(gp_Ax2(gp::Origin(), gp::DY()));
    const TopoDS_Shape m = BRepBuilderAPI_Transform(s, mirror, true).Shape();
    check("mirrored (XZ plane)", m, v0);
    gp_Trsf move;
    move.SetRotation(gp::OX(), 0.7);
    move.SetTranslationPart(gp_Vec(1, 2, 3));
    check("moved, copied", BRepBuilderAPI_Transform(s, move, true).Shape(), v0);
    check("moved, not copied", BRepBuilderAPI_Transform(s, move, false).Shape(), v0);
    gp_Trsf scale;
    scale.SetScale(gp::Origin(), 2.);
    check("scaled by 2", BRepBuilderAPI_Transform(s, scale, true).Shape(), 8. * v0);

    BRepAlgoAPI_Common common(s, m);
    BRepAlgoAPI_Fuse   fuse(s, m);
    if (!fuse.IsDone() || !common.IsDone()) {
        printf("%-22s BAD not done\n", "fused with its mirror");
        bad++;
    }
    else
        check("fused with its mirror", fuse.Shape(), 2. * v0 - volume(common.Shape()));
    if (dir) {
        BRepTools::Write(m, (std::string(dir) + "/mirror.brep").c_str());
        if (fuse.IsDone())
            BRepTools::Write(fuse.Shape(), (std::string(dir) + "/fuse.brep").c_str());
    }
    printf("%d bad\n", bad);
    return bad != 0;
}
