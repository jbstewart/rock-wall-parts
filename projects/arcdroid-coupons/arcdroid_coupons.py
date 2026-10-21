"""ArcDroid plasma cut-profile coupons — two test pieces, one script.

Spec: ~/PP/pp-operations/areas/fabrication/ArcDroid-Cut-Profile-Runbook.md,
sections 5, 7, 8, 9, 10, 13. That runbook is the source of truth for what these
coupons are FOR; this script is the source of truth for their geometry.

  profile coupon   three squares (1/2/4") + a five-hole column, on a drop that
                   stays a drop. Squares give kerf = (H-S)/2 and path = (H+S)/2
                   (section 7) and the constant-vs-scale machine check (section 5).
                   The hole column gives the hole floor (section 8).

  flat-bar test    1.25 x 42 bar spanning the X2 transition: two 1/4" holes for
                   X pitch error, one long line for Y step and rotation
                   (section 13). Replaces the retired X2-Test.

Nothing on either coupon is an outline. Both blanks stay whole, because a freed
part moves while the rest is still being cut and every number here is a
measurement off the skeleton as well as the slug.

Run:  .venv/bin/python projects/arcdroid-coupons/arcdroid_coupons.py
"""

import re
import sys
from pathlib import Path

import ezdxf
from build123d import Circle, Line, Pos, Rectangle, Unit
from build123d.exporters import ExportDXF

# ------------------------------------------------------------------ revision

REV = "A"
REV_TAG = f"rev{REV}"

HERE = Path(__file__).parent
OUT_DIR = HERE / "output"
BRIEF = HERE / "BRIEF.md"

# ---------------------------------------------------------------- parameters

THICK = 0.125            # 1/8" mild steel, both coupons
KERF = 0.055             # measured 2026-10-20, 1.4 mm — runbook section 12

# --- profile coupon ---------------------------------------------------------
# Blank X is NOT the runbook's "about 6 by 10". The three squares plus their 1"
# webs span 9.000, and with the 1" edge margins the spec demands that is 11.000
# of X before the hole column is placed at all — 10.000 cannot hold it. Minimum
# honest blank is 12.375; rounded UP to the next 1/2" (house rule) that is
# 12.500. Y stays at the spec'd 6.000, which the 4" square fills exactly to its
# 1" margins. See BRIEF.md "Blank size" for the full arithmetic.
PC_W = 12.500
PC_H = 6.000

SQUARES = [1.0, 2.0, 4.0]      # section 7: kerf is size-independent; 1 vs 4 is section 5
SQ_WEB = 1.0                   # steel left between adjacent squares
MARGIN = 1.0                   # minimum steel from any feature to any blank edge

HOLE_DIAS = [0.125, 0.1875, 0.250, 0.3125, 0.375]   # 1/8 .. 3/8, section 8
HOLE_PITCH = 0.75                                    # centre-to-centre
SMALL_HOLE_MAX = 0.1875        # under 3/16 goes in the small-hole op (runbook s.9)

# The 1" feature-to-feature rule is deliberately NOT applied inside the hole
# column: the runbook fixes that column at a 3/4" pitch, so the rule and the
# spec cannot both hold. The 1" rule exists to keep two large cutouts' heat
# fields and kerf error out of each other; inside the column the governing
# number is the web between adjacent holes, checked below against MIN_HOLE_WEB.
MIN_HOLE_WEB = 3.0 * THICK     # 0.375 — a web the torch can leave on 1/8 plate

# --- flat-bar registration test --------------------------------------------
FB_W = 42.0
FB_H = 1.25
FB_HOLE_DIA = 0.250
FB_HOLE_X = [20.0, 22.0]       # X pitch error over a known 2.000
FB_LINE_Y = 0.250              # from the lower long edge
FB_LINE_X = (16.0, 26.0)       # 5" either side of the 21" split
FB_SPLIT_X = 21.0              # 533 mm — set in SimpleTrace, NOT in this geometry
FB_MIN_CLEAR = 0.250           # line-to-hole and hole-to-edge

# ----------------------------------------------------------------- filenames

PC_DXF = OUT_DIR / f"arcdroid-profile-coupon-{REV_TAG}.dxf"
FB_DXF = OUT_DIR / f"arcdroid-flatbar-test-{REV_TAG}.dxf"
CAM_MD = OUT_DIR / f"arcdroid-coupons-camsheet-{REV_TAG}.md"

TOL = 1e-9


class CheckFailure(Exception):
    pass


_checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global _checks
    _checks += 1
    if not ok:
        raise CheckFailure(f"{label}{(' — ' + detail) if detail else ''}")
    print(f"  ok  {label}{(' — ' + detail) if detail else ''}")


# ------------------------------------------------------------------- layout


def profile_layout() -> dict:
    """Squares left to right on a shared centreline, hole column to their right."""
    cy = PC_H / 2
    squares, x = [], MARGIN
    for s in SQUARES:
        squares.append({"size": s, "x0": x, "y0": cy - s / 2, "cx": x + s / 2, "cy": cy})
        x += s + SQ_WEB
    right_of_squares = x - SQ_WEB          # undo the trailing web

    # Hole column: biggest hole's edge sits MARGIN clear of the squares.
    col_x = right_of_squares + MARGIN + max(HOLE_DIAS) / 2
    span = HOLE_PITCH * (len(HOLE_DIAS) - 1)
    holes = [
        {"dia": d, "cx": col_x, "cy": cy - span / 2 + i * HOLE_PITCH}
        for i, d in enumerate(HOLE_DIAS)   # ascending, 1/8 at the bottom
    ]
    return {"squares": squares, "holes": holes, "col_x": col_x,
            "squares_right": right_of_squares}


def flatbar_layout() -> dict:
    cy = FB_H / 2
    holes = [{"dia": FB_HOLE_DIA, "cx": x, "cy": cy} for x in FB_HOLE_X]
    line = ((FB_LINE_X[0], FB_LINE_Y), (FB_LINE_X[1], FB_LINE_Y))
    return {"holes": holes, "line": line}


# -------------------------------------------------------------------- checks


def _gap_rect_rect(a: dict, b: dict) -> float:
    ax1, ay1 = a["x0"] + a["size"], a["y0"] + a["size"]
    bx1, by1 = b["x0"] + b["size"], b["y0"] + b["size"]
    dx = max(b["x0"] - ax1, a["x0"] - bx1)
    dy = max(b["y0"] - ay1, a["y0"] - by1)
    return max(dx, dy)


def _gap_rect_circle(r: dict, c: dict) -> float:
    rx1, ry1 = r["x0"] + r["size"], r["y0"] + r["size"]
    dx = max(r["x0"] - c["cx"], c["cx"] - rx1, 0.0)
    dy = max(r["y0"] - c["cy"], c["cy"] - ry1, 0.0)
    return (dx * dx + dy * dy) ** 0.5 - c["dia"] / 2


def check_profile(L: dict) -> None:
    print("\nprofile coupon")
    check([s["size"] for s in L["squares"]] == SQUARES,
          "squares are exactly 1, 2 and 4 inch", str(SQUARES))
    check(len({round(s["cy"], 9) for s in L["squares"]}) == 1,
          "the three squares sit in ONE row", f"centreline y={L['squares'][0]['cy']:.3f}")

    for s in L["squares"]:
        m = min(s["x0"], s["y0"], PC_W - (s["x0"] + s["size"]), PC_H - (s["y0"] + s["size"]))
        check(m >= MARGIN - TOL, f"{s['size']:g}\" square clears every blank edge",
              f"min {m:.4f} >= {MARGIN}")

    for a, b in zip(L["squares"], L["squares"][1:]):
        g = _gap_rect_rect(a, b)
        check(g >= SQ_WEB - TOL, f"web between {a['size']:g}\" and {b['size']:g}\" squares",
              f"{g:.4f} >= {SQ_WEB}")

    for h in L["holes"]:
        m = min(h["cx"], h["cy"], PC_W - h["cx"], PC_H - h["cy"]) - h["dia"] / 2
        check(m >= MARGIN - TOL, f"{h['dia']:.4f}\" hole clears every blank edge",
              f"min {m:.4f} >= {MARGIN}")

    worst = min(_gap_rect_circle(s, h) for s in L["squares"] for h in L["holes"])
    check(worst >= MARGIN - TOL, "every hole clears every square by 1 inch",
          f"worst {worst:.4f} >= {MARGIN}")

    pitches = [b["cy"] - a["cy"] for a, b in zip(L["holes"], L["holes"][1:])]
    check(all(abs(p - HOLE_PITCH) < TOL for p in pitches),
          "hole column holds the 3/4 inch pitch", f"{pitches[0]:.4f}")

    webs = [(b["cy"] - a["cy"]) - (a["dia"] + b["dia"]) / 2
            for a, b in zip(L["holes"], L["holes"][1:])]
    check(min(webs) >= MIN_HOLE_WEB - TOL,
          "web between adjacent holes is producible on 1/8 plate",
          f"min {min(webs):.4f} >= {MIN_HOLE_WEB:.4f} (3x thickness)")
    check(min(webs) >= 2 * KERF, "that web is wider than two kerfs",
          f"{min(webs):.4f} >= {2 * KERF:.4f}")

    check(sorted(h["dia"] for h in L["holes"]) == sorted(HOLE_DIAS),
          "hole column holds exactly the five specified diameters")


def check_flatbar(L: dict) -> None:
    print("\nflat-bar registration test")
    for h in L["holes"]:
        edge = min(h["cy"], FB_H - h["cy"]) - h["dia"] / 2
        check(edge >= FB_MIN_CLEAR - TOL, f"hole at X={h['cx']:g} leaves steel to both bar edges",
              f"{edge:.4f} >= {FB_MIN_CLEAR}")
        check(min(h["cx"], FB_W - h["cx"]) - h["dia"] / 2 >= FB_MIN_CLEAR - TOL,
              f"hole at X={h['cx']:g} clears both bar ends")

    (x0, y0), (x1, _) = L["line"]
    for h in L["holes"]:
        # the line runs the full X range of both holes, so the gap is in Y alone
        check(x0 <= h["cx"] - h["dia"] / 2 and x1 >= h["cx"] + h["dia"] / 2,
              f"line spans hole at X={h['cx']:g} in X (so Y decides the clearance)")
        gap = abs(h["cy"] - y0) - h["dia"] / 2
        check(gap > 0, f"line does not intersect the hole at X={h['cx']:g}", f"{gap:.4f} > 0")
        check(gap >= FB_MIN_CLEAR - TOL, f"line clears the hole at X={h['cx']:g}",
              f"{gap:.4f} >= {FB_MIN_CLEAR}")

    check(y0 - 0 >= FB_MIN_CLEAR - TOL, "line clears the lower long edge", f"{y0:.4f}")
    check(0 < x0 and x1 < FB_W, "line lies inside the bar", f"X {x0:g}..{x1:g} in 0..{FB_W:g}")
    check(abs((x0 + x1) / 2 - FB_SPLIT_X) < TOL,
          "line is centred on the X2 split", f"mid {(x0 + x1) / 2:g} = {FB_SPLIT_X:g}\"")
    check(abs(FB_HOLE_X[1] - FB_HOLE_X[0] - 2.0) < TOL,
          "hole pitch is a round 2.000 to measure against")


def check_inside_blank(shapes, w: float, h: float, label: str) -> None:
    for layer, shp in shapes:
        bb = shp.bounding_box()
        ok = (bb.min.X >= -TOL and bb.min.Y >= -TOL
              and bb.max.X <= w + TOL and bb.max.Y <= h + TOL)
        check(ok, f"{label}: {layer} geometry lies inside the blank",
              f"bbox X {bb.min.X:.3f}..{bb.max.X:.3f}  Y {bb.min.Y:.3f}..{bb.max.Y:.3f}")


def check_brief() -> None:
    print("\nbrief")
    check(BRIEF.exists(), "BRIEF.md exists")
    txt = BRIEF.read_text()
    m = re.search(r"^Current revision:\s*\*\*Rev ([A-Z]+)\*\*", txt, re.M)
    check(bool(m), "BRIEF.md declares a current revision")
    check(m.group(1) == REV, "BRIEF.md revision matches the script", f"Rev {m.group(1)}")
    # the brief is a decision log, hand-kept — so cross-check its numbers instead
    for want, what in [(f"{PC_W:g} x {PC_H:g}", "profile blank"),
                       (f"{FB_H:g} x {FB_W:g}", "flat bar"),
                       (f"{HOLE_PITCH:g}", "hole pitch")]:
        check(want in txt, f"BRIEF.md states the {what} this script builds", want)


# -------------------------------------------------------------------- export


def build_profile(L: dict):
    out = []
    for s in L["squares"]:
        out.append(("SQUARES", (Pos(s["cx"], s["cy"]) * Rectangle(s["size"], s["size"])).faces()[0]))
    for h in L["holes"]:
        layer = "HOLES_SMALL" if h["dia"] < SMALL_HOLE_MAX else "HOLES"
        out.append((layer, (Pos(h["cx"], h["cy"]) * Circle(h["dia"] / 2)).faces()[0]))
    return out


def build_flatbar(L: dict):
    out = [("HOLES", (Pos(h["cx"], h["cy"]) * Circle(h["dia"] / 2)).faces()[0])
           for h in L["holes"]]
    (x0, y0), (x1, y1) = L["line"]
    out.append(("LINE", Line((x0, y0), (x1, y1)).edges()[0]))
    return out


def export(shapes, path: Path) -> None:
    ex = ExportDXF(unit=Unit.IN)
    for layer in dict.fromkeys(l for l, _ in shapes):      # stable, deduped
        ex.add_layer(layer)
    for layer, shp in shapes:
        ex.add_shape(shp, layer=layer)
    ex.write(path)


def close_squares(path: Path, squares: list[dict]) -> None:
    """Re-emit the squares as closed LWPOLYLINEs.

    ExportDXF writes a rectangle face as four loose LINE entities. Fusion will
    chain them, but then the entity count no longer equals the contour count --
    and counting toolpaths against contours is the only way to catch Fusion
    silently dropping one. One closed polyline per square makes that count mean
    something, and makes the squares op a single-click selection.
    """
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    for e in [e for e in msp if e.dxf.layer == "SQUARES"]:
        msp.delete_entity(e)
    for s in squares:
        x0, y0, n = s["x0"], s["y0"], s["size"]
        msp.add_lwpolyline(
            [(x0, y0), (x0 + n, y0), (x0 + n, y0 + n), (x0, y0 + n)],
            close=True, dxfattribs={"layer": "SQUARES"},
        )
    doc.saveas(path)


# ------------------------------------------------------- re-import + verify


def verify(path: Path, expect: dict, label: str) -> dict:
    """Re-read what we just wrote and prove the layers survived the round trip."""
    print(f"\nre-import {path.name}")
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    tally: dict[str, list] = {}
    for e in msp:
        tally.setdefault(e.dxf.layer, []).append(e)

    check(set(tally) == set(expect), f"{label}: layers present",
          f"{sorted(tally)}")
    check("0" not in tally, f"{label}: nothing landed on layer 0")

    for layer, want in expect.items():
        got = tally[layer]
        check(len(got) == want["count"], f"{label}: {layer} entity count",
              f"{len(got)} == {want['count']}")
        kinds = sorted({e.dxftype() for e in got})
        print(f"      {layer}: {len(got)}x {','.join(kinds)}")
        if "dias" in want:
            dias = sorted(round(e.dxf.radius * 2, 6) for e in got)
            check(dias == sorted(round(d, 6) for d in want["dias"]),
                  f"{label}: {layer} holds exactly the specified diameters",
                  f"{[f'{d:.4f}' for d in dias]}")
            cent = sorted((round(e.dxf.center.x, 6), round(e.dxf.center.y, 6)) for e in got)
            want_c = sorted((round(x, 6), round(y, 6)) for x, y in want["centres"])
            check(cent == want_c, f"{label}: {layer} hole centres", f"{cent}")
        if "corners" in want:
            check(all(e.dxftype() == "LWPOLYLINE" and e.closed for e in got),
                  f"{label}: {layer} are CLOSED polylines, one per contour")
            got_sq = sorted(
                (round(min(v[0] for v in e.get_points("xy")), 6),
                 round(min(v[1] for v in e.get_points("xy")), 6),
                 round(max(v[0] for v in e.get_points("xy"))
                       - min(v[0] for v in e.get_points("xy")), 6))
                for e in got)
            check(got_sq == sorted((round(a, 6), round(b, 6), round(c, 6))
                                   for a, b, c in want["corners"]),
                  f"{label}: {layer} corners and sizes", f"{got_sq}")
        if "ends" in want:
            e = got[0]
            ends = ((round(e.dxf.start.x, 6), round(e.dxf.start.y, 6)),
                    (round(e.dxf.end.x, 6), round(e.dxf.end.y, 6)))
            check(sorted(ends) == sorted(want["ends"]), f"{label}: {layer} endpoints", f"{ends}")
    return tally


# ----------------------------------------------------------------- cam sheet


def cam_sheet(pc_tally: dict, fb_tally: dict) -> str:
    n_sq = len(pc_tally["SQUARES"])
    L = []
    A = L.append
    A(f"# ArcDroid cut-profile coupons — CAM Sheet  (Rev {REV})")
    A("")
    A("Generated by `arcdroid_coupons.py` at Rev A — regenerate, don't hand-edit.")
    A("")
    A("Source of truth for WHY: `areas/fabrication/ArcDroid-Cut-Profile-Runbook.md` in")
    A("pp-operations, sections 5, 7, 8, 9, 10 and 13. This sheet is the how.")
    A("")
    A("Import each DXF: **Insert DXF, Units = Inch** (the dialog ignores the file's declared")
    A("units), with **one sketch per layer** turned ON. Each op below then selects its own")
    A("sketch and nothing else — never pick contours individually.")
    A("")
    A("## Tool — both coupons, every op")
    A("")
    A("| Field | Value |")
    A("|---|---|")
    A("| Tool | `ArcDroid Ti65 steel 1/8`, from the **Local** library |")
    A("| Preset | `1/8 Steel` |")
    A("| Kerf width (Cutter tab) | **1.4 mm** (0.055\", measured 2026-10-20) |")
    A("")
    A("Pick the tool from Local FIRST, then set the preset — re-picking a tool resets the")
    A("preset to Default. No op may read Default when you post.")
    A("")
    A(f"## 1 — `arcdroid-profile-coupon-{REV_TAG}.dxf`")
    A("")
    A(f"Blank: **{PC_W:g} x {PC_H:g}\"** drop of 1/8 mild steel. Nothing frees it; it stays a drop.")
    A("")
    A("| Op | Layer | Geometry | Sideways comp | Comp type | Lead-in / out | Pierce clearance | Tabs |")
    A("|---|---|---|---|---|---|---|---|")
    A(f"| 1 | `SQUARES` | {n_sq} squares (1, 2, 4\") | **Center** | — | **both off** | default | none |")
    A("| 2 | `HOLES_SMALL` | 1x 1/8\" hole | **Left** | **In computer** | **in: 0.020 linear, perpendicular, radius 0** | **0.020 in (0.5 mm)** | none |")
    A("| 3 | `HOLES` | 4x 3/16, 1/4, 5/16, 3/8\" | **Left** | **In computer** | stock | default 0.059 in (1.5 mm) | none |")
    A("")
    A("Center comp on the squares is deliberate and is the whole point of op 1: the torch")
    A("runs ON the drawn line, so the slug comes out one kerf under and the hole one kerf")
    A("over, and `kerf = (H - S) / 2` cancels the drawn size. Do not \"fix\" it to Left.")
    A("")
    A("0.020 pierce clearance on op 2 is the floor that lets a 1/8\" hole generate with")
    A("lead-in on. Fusion silently DROPS any contour where lead-in plus clearance won't fit")
    A("inside the hole — a dropped contour is a hole that never gets cut, with no error.")
    A("After Generate, count the toolpaths against the contour counts in the table above.")
    A("")
    A(f"## 2 — `arcdroid-flatbar-test-{REV_TAG}.dxf`")
    A("")
    A(f"Blank: **{FB_H:g} x {FB_W:g}\"** 1/8 mild steel flat bar. Nothing frees it.")
    A("")
    A("| Op | Layer | Geometry | Sideways comp | Comp type | Lead-in / out | Pierce clearance | Tabs |")
    A("|---|---|---|---|---|---|---|---|")
    A(f"| 1 | `HOLES` | 2x 1/4\" at X={FB_HOLE_X[0]:g} and {FB_HOLE_X[1]:g} | **Left** | **In computer** | stock | default 0.059 in (1.5 mm) | none |")
    A(f"| 2 | `LINE` | 1 open line, X {FB_LINE_X[0]:g} to {FB_LINE_X[1]:g} | **none** (open contour) | — | **off** | default | none |")
    A("")
    A(f"**The X2 split is NOT in this geometry.** Set it in SimpleTrace at **533 mm** ({FB_SPLIT_X:g}\").")
    A("The line is drawn straight through that station on purpose — the step you are")
    A("measuring is the machine's, and it only appears if the geometry has none.")
    A("")
    A("Controller profile for 1/8 steel, confirm before cutting (runbook section 12):")
    A("")
    A("| | |")
    A("|---|---|")
    A("| Units | mm |")
    A("| Feed | 2200 mm/min |")
    A("| Clear / Pierce / Cut Z | 2 / 2 / 2 mm |")
    A("| Pierce delay | 1.0 s |")
    A("| Off delay | 0.1 s |")
    A("| Kerf | **0** (Fusion does the offset) |")
    A("| Titanium 65 | 50 A |")
    A("| Air, torch firing | 80 psi (5.5 bar) |")
    A("")
    A("## Posting")
    A("")
    A("- Post both setups with the **RWF ArcDroid post**, **Unit = Millimeters** in the Post dialog.")
    A("- Compare the first ten lines of each output against the last known-good file.")
    A("- Setup sheet: **Post Process with `rwf-setup-sheet.cps`** — NOT the right-click Setup")
    A("  Sheet, which is hard-wired to Autodesk's. Write the split X in mm on the flat-bar sheet.")
    A("")
    A("## Measuring (runbook sections 5, 7, 8, 13)")
    A("")
    A("Let it cool. Measure the **top face** — plasma kerf is wider at the top, and the top is")
    A("the face that shows. Keep away from the pierce and lead-out.")
    A("")
    A("- Squares, each in X and Y: **S** across the slug (outside jaws), **H** across the hole")
    A(f"  left in the skeleton (inside jaws). `kerf = (H - S) / 2`, `path = (H + S) / 2`.")
    A("  Average kerf over all three; X and Y should agree within 0.005.")
    A("- Compare the 1\" and 4\" paths: same Y shortfall on both = a constant loss per contour.")
    A("  Four times the shortfall on the 4\" = a scale error. Record both; do not fudge it in CAM.")
    A("- Holes: diameter in two directions, and look at the pierce. Round within 0.005 and on")
    A("  size within 0.010 passes. The floor is the smallest hole that passes.")
    A(f"- Flat bar: hole pitch {FB_HOLE_X[0]:g} to {FB_HOLE_X[1]:g} gives X error. Step in the line at the split")
    A("  gives Y error. Straightedge on the A half, gap at the far end of the B half, divide")
    A("  by 5, gives rotation.")
    A("")
    return "\n".join(L) + "\n"


# -------------------------------------------------------------------- driver


def main() -> int:
    print(f"ArcDroid coupons — Rev {REV}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pc = profile_layout()
    fb = flatbar_layout()

    check_profile(pc)
    check_flatbar(fb)
    check_brief()

    pc_shapes = build_profile(pc)
    fb_shapes = build_flatbar(fb)

    print("\nblank containment")
    check_inside_blank(pc_shapes, PC_W, PC_H, "profile coupon")
    check_inside_blank(fb_shapes, FB_W, FB_H, "flat bar")

    export(pc_shapes, PC_DXF)
    close_squares(PC_DXF, pc["squares"])
    export(fb_shapes, FB_DXF)

    small = [h for h in pc["holes"] if h["dia"] < SMALL_HOLE_MAX]
    big = [h for h in pc["holes"] if h["dia"] >= SMALL_HOLE_MAX]
    pc_tally = verify(PC_DXF, {
        "SQUARES": {"count": len(SQUARES),
                    "corners": [(s["x0"], s["y0"], s["size"]) for s in pc["squares"]]},
        "HOLES_SMALL": {"count": len(small),
                        "dias": [h["dia"] for h in small],
                        "centres": [(h["cx"], h["cy"]) for h in small]},
        "HOLES": {"count": len(big),
                  "dias": [h["dia"] for h in big],
                  "centres": [(h["cx"], h["cy"]) for h in big]},
    }, "profile coupon")

    fb_tally = verify(FB_DXF, {
        "HOLES": {"count": len(fb["holes"]),
                  "dias": [h["dia"] for h in fb["holes"]],
                  "centres": [(h["cx"], h["cy"]) for h in fb["holes"]]},
        "LINE": {"count": 1, "ends": list(fb["line"])},
    }, "flat bar")

    CAM_MD.write_text(cam_sheet(pc_tally, fb_tally))

    print(f"\nwrote {PC_DXF.relative_to(HERE.parent.parent)}")
    print(f"wrote {FB_DXF.relative_to(HERE.parent.parent)}")
    print(f"wrote {CAM_MD.relative_to(HERE.parent.parent)}")
    print(f"\n{_checks} checks passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckFailure as e:
        print(f"\nCHECK FAILED: {e}", file=sys.stderr)
        sys.exit(1)
