"""Artwork cut-density coupon — proves MAX_THIN_RUN on steel before a 41" blank.

The gate in bonebrake_assembly says no run of too-thin material may exceed
MAX_THIN_RUN (8x material thickness). That number is reasoning about heat
sinking, not a measurement. This coupon turns it into one.

Three zones on ONE uncut piece, so flatness can be checked across the whole
thing -- flatness is what actually decides whether the face seats on the frame:

  A  the densest band of the REAL art, lifted straight out of panel_sketch()
     so the coupon geometry is provably what the panel will get
  B  a second band of real art holding the worst CUT-AWAY ribbon, which lives
     nowhere near zone A
  C  a calibration ladder of parallel-sided webs, width x length, bracketing
     what the real art contains -- this is the zone that locates the limit
     instead of merely passing or failing at it

Run:  .venv/bin/python projects/bonebrake-cover/cutcoupon.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build123d import Pos, Rectangle, RectangleRounded, Unit
from build123d.exporters import ExportDXF

import bonebrake_assembly as ba

# ---------------------------------------------------------------- the zones

ZONE_A = (-13.4, -9.4)   # panel y: densest band, worst steel run, one pilot row
ZONE_B = (4.5, 6.5)      # panel y: worst art ribbon

# Web widths. The WEB is the specimen, not the slots either side of it, so
# every rung has to be a web the torch can actually leave behind: narrower
# than one kerf and the two cuts are closer together than the arc is wide,
# which is where comp error and kerf variation merge them into one hole.
# A 0.040 rung shipped in Rev D at 0.73x kerf — below the art's own thinnest
# feature (0.0700) and a third of MIN_WEB, so it could only ever have failed,
# and Fusion fused its pairs rather than post it. Replaced by 0.140, which
# puts rungs either side of the MIN_WEB gate (0.120 / 0.140 vs 0.1196) where
# the answer actually matters. Lowest rung 0.060 = 1.09x kerf: producible,
# and deliberately marginal, because that is the question being asked.
LADDER_W = [0.060, 0.080, 0.100, 0.120, 0.140]          # web widths
LADDER_L = [0.25, 0.50, 1.00, 2.00]                     # web lengths
SLOT = 0.18          # cut-away either side of each web; > 2x kerf so it opens
ROW_GAP = 0.30
CELL_GAP = 0.40

MARGIN = 0.45
ZONE_GAP = 0.40
CLIP = 0.50          # corner clip: orientation key, so the sheet is unambiguous

COUPON_W = ba.W      # full panel width — keeps real edge distances and heat paths

OUT_DXF = ba.OUT_DIR / f"{ba.BASENAME}-cutcoupon-{ba.REV_TAG}.dxf"
OUT_SHEET = ba.OUT_DIR / f"{ba.BASENAME}-cutcoupon-{ba.REV_TAG}.md"


def ladder_height() -> float:
    return sum(2 * SLOT + w for w in LADDER_W) + ROW_GAP * (len(LADDER_W) - 1)


def layout() -> dict:
    """Stack the zones bottom-up, then centre the blank on the origin."""
    h_c = ladder_height()
    h_a = ZONE_A[1] - ZONE_A[0]
    h_b = ZONE_B[1] - ZONE_B[0]
    raw = MARGIN + h_c + ZONE_GAP + h_b + ZONE_GAP + h_a + MARGIN
    total = -(-raw // 0.5) * 0.5          # round UP to the next 1/2", house rule
    slack = total - raw
    y = -total / 2 + MARGIN
    c0 = y; y += h_c + ZONE_GAP
    b0 = y; y += h_b + ZONE_GAP
    a0 = y
    return {
        "total_h": total, "slack": slack,
        "ladder_y0": c0,
        "B_dy": (b0 + h_b / 2) - (ZONE_B[0] + h_b / 2),
        "A_dy": (a0 + h_a / 2) - (ZONE_A[0] + h_a / 2),
    }


def art_band(art, lo: float, hi: float):
    """Material of the real face panel between two panel-y values."""
    strip = Pos(0, (lo + hi) / 2) * Rectangle(COUPON_W, hi - lo)
    return ba.panel_sketch(art, pilots=True) & strip


def ladder_cells(y0: float):
    """Yield (web_width, web_length, cx, cy, lower_slot, upper_slot)."""
    row_w = sum(LADDER_L) + CELL_GAP * (len(LADDER_L) - 1)
    y = y0
    for w in LADDER_W:
        x = -row_w / 2
        for L in LADDER_L:
            cx = x + L / 2
            low = Pos(cx, y + SLOT / 2) * Rectangle(L, SLOT)
            web_c = y + SLOT + w / 2
            up = Pos(cx, y + SLOT + w + SLOT / 2) * Rectangle(L, SLOT)
            yield w, L, cx, web_c, low, up
            x += L + CELL_GAP
        y += 2 * SLOT + w + ROW_GAP


def build(art):
    lay = layout()
    blank = RectangleRounded(COUPON_W, lay["total_h"], 0.125)

    sk = blank
    for (lo, hi), dy in ((ZONE_A, lay["A_dy"]), (ZONE_B, lay["B_dy"])):
        foot = Pos(0, (lo + hi) / 2 + dy) * Rectangle(COUPON_W, hi - lo)
        mat = Pos(0, dy) * art_band(art, lo, hi)
        sk = sk - (foot - mat)          # subtract only what the panel cuts away

    for _w, _L, _cx, _cy, low, up in ladder_cells(lay["ladder_y0"]):
        sk = sk - low - up

    # orientation key: clip the top-left corner
    sk = sk - Pos(-COUPON_W / 2, lay["total_h"] / 2) * Rectangle(
        2 * CLIP, 2 * CLIP)
    return sk, lay


def checks(sk, lay, art) -> list[tuple[str, bool, str]]:
    cuts = ba.thin_features(art)
    inA = [r for r in cuts["webs"] if ZONE_A[0] <= r["y"] <= ZONE_A[1]]
    inB = [r for r in cuts["slivers"] if ZONE_B[0] <= r["y"] <= ZONE_B[1]]
    worst_w = max(cuts["webs"], key=lambda r: r["len"])
    worst_s = max(cuts["slivers"], key=lambda r: r["len"])
    return [
        ("coupon is ONE connected piece (flatness is measured across it)",
         len(sk.faces()) == 1, f"{len(sk.faces())} face(s)"),
        ("ladder slots open under the normal-comp recipe",
         SLOT >= 2 * ba.PLASMA_KERF,
         f"slot {SLOT:.3f} >= 2 x kerf {2 * ba.PLASMA_KERF:.3f}"),
        # The slot check above says the HOLES open. This says the WEBS between
        # them survive being cut — the specimen, and the thing Rev D missed.
        ("every ladder web is wider than one kerf",
         min(LADDER_W) > ba.PLASMA_KERF,
         f"narrowest web {min(LADDER_W):.3f} = "
         f"{min(LADDER_W) / ba.PLASMA_KERF:.2f}x kerf {ba.PLASMA_KERF:.3f}"
         + (f"; {sum(1 for w in LADDER_W if w < 1.5 * ba.PLASMA_KERF)} rung(s) "
            f"under 1.5x kerf are marginal by design"
            if any(w < 1.5 * ba.PLASMA_KERF for w in LADDER_W) else "")),
        ("ladder brackets the real art's thickness range",
         min(LADDER_W) < min(r["thick"] for r in cuts["webs"])
         and max(LADDER_W) > max(r["thick"] for r in cuts["webs"]),
         f"ladder {min(LADDER_W):.3f}..{max(LADDER_W):.3f} brackets art "
         f"{min(r['thick'] for r in cuts['webs']):.4f}.."
         f"{max(r['thick'] for r in cuts['webs']):.4f}"),
        ("ladder spans the gate (cells either side of MAX_THIN_RUN)",
         min(LADDER_L) < ba.MAX_THIN_RUN < max(LADDER_L),
         f"lengths {min(LADDER_L):.2f}..{max(LADDER_L):.2f} span "
         f"MAX_THIN_RUN {ba.MAX_THIN_RUN:.3f}"),
        ("zone A carries the worst steel run on the panel",
         ZONE_A[0] <= worst_w["y"] <= ZONE_A[1],
         f"worst run {worst_w['len']:.3f} at panel y {worst_w['y']:+.3f}; "
         f"{len(inA)} of {len(cuts['webs'])} steel ribbons in zone A"),
        ("zone B carries the worst art run on the panel",
         ZONE_B[0] <= worst_s["y"] <= ZONE_B[1],
         f"worst run {worst_s['len']:.3f} at panel y {worst_s['y']:+.3f}; "
         f"{len(inB)} of {len(cuts['slivers'])} art ribbons in zone B"),
        ("blank rounds up to a 1/2 inch",
         abs(lay["total_h"] * 2 - round(lay["total_h"] * 2)) < 1e-9,
         f"{COUPON_W:.3f} x {lay['total_h']:.3f} (slack {lay['slack']:.3f})"),
        ("BRIEF current revision matches script REV",
         f"Current revision: **{ba.REV}**" in ba.BRIEF_PATH.read_text(),
         f'BRIEF.md says Rev {ba.REV}'),
    ], cuts, inA, inB


def sheet(lay, cuts, inA, inB) -> str:
    L = []
    L.append(f"# Bonebrake artwork cut coupon — acceptance sheet (Rev {ba.REV})")
    L.append("")
    L.append(f"Generated by cutcoupon.py at Rev {ba.REV} — regenerate, don't hand-edit.")
    L.append(f"Program: `{OUT_DXF.name}`. Blank {COUPON_W:.3f} x {lay['total_h']:.3f}, "
             f"11ga mild steel, same lot as the panels.")
    L.append("")
    L.append("## Why this exists")
    L.append("")
    L.append(f"The generation gate says no run of too-thin material may exceed "
             f"**{ba.MAX_THIN_RUN:.3f}\"** (8 x material thickness). That is reasoning about "
             f"heat sinking, not a measurement. The artwork currently clears it "
             f"{ba.MAX_THIN_RUN / cuts['longest_web_run']:.1f}x "
             f"(longest steel run {cuts['longest_web_run']:.3f}), but the limit itself has "
             f"never been proven on this machine. Zone C locates it.")
    L.append("")
    # Pilots that land inside a zone come across with it, and they are the ones
    # the default linking constraints silently discard.
    n_pilot = sum(
        1 for _, py in ba.corner_pattern() + ba.rivet_pattern()
        if ZONE_A[0] <= py <= ZONE_A[1] or ZONE_B[0] <= py <= ZONE_B[1]
    )
    L.append("## Cut it the way the panel will be cut")
    L.append("")
    L.append("- **TWO ops, ONE gcode file.** Operations are not programs: post the SETUP")
    L.append("  and Fusion writes both ops into a single NC file, in browser-tree order.")
    L.append("  Same torch in both, so no tool change. Put the pilot op FIRST, so the holes")
    L.append("  are pierced while the blank is still fully attached and rigid.")
    L.append(f"- The DXF ships on two layers — **`PILOTS`** ({n_pilot} circles) and **`CUTS`**")
    L.append("  (everything else). Insert DXF with the **one-sketch-per-layer** option on, then")
    L.append("  each op selects a whole sketch. Never pick contours by hand on this file.")
    L.append(f"- The {n_pilot} pilot circles go in their own holes-only op:")
    L.append("  Sideways Compensation = **Center**, Lead-In (Entry) and")
    L.append("  Lead-Out (Exit) both **unchecked**, Pierce Clearance = **0.00 in**. The")
    L.append(f"  default 0.059 pierce clearance plus a 0.020 lead needs 0.079 inside a")
    L.append(f"  {ba.PILOT_DIA / 2:.4f} radius, so Fusion discards the pass and the hole never")
    L.append("  gets cut. Everything else (art, outline, ladder slots) is a normal-comp op")
    L.append("  with standard leads, and must NOT include the pilot circles.")
    L.append("- Same CAM setup as the panel programs (see the CAM sheet), same consumables")
    L.append("  at their current wear state — note the tip hours on this sheet.")
    L.append("- **Same cut ordering and the same back-to-back timing.** A coupon cut")
    L.append("  leisurely, with cooling between adjacent contours, tells you nothing about a")
    L.append("  panel cut continuously. This is the usual way coupons mislead.")
    L.append("- Same hold-down as the panel. Do not separate the zones.")
    L.append("- Orientation key: the clipped corner is TOP LEFT, art side up.")
    L.append("")
    L.append("## Zone C — calibration ladder (the point of the coupon)")
    L.append("")
    L.append(f"Parallel-sided webs. Width is the finished web; normal comp puts the kerf on "
             f"the waste side, so the DXF nominal is what you measure against. "
             f"Rows bottom to top, cells left to right.")
    L.append("")
    L.append("| web width | 0.25 long | 0.50 long | 1.00 long | 2.00 long |")
    L.append("|---|---|---|---|---|")
    for w in LADDER_W:
        L.append(f"| **{w:.3f}** | | | | |")
    L.append("")
    L.append("Record per cell: `OK` / `curled` / `blown through`. The transition from OK to")
    L.append(f"failed across the 1.00 and 2.00 columns is the real `MAX_THIN_RUN`. If 0.100 x")
    L.append(f"2.00 survives, the gate is too conservative; if 0.120 x 1.00 fails, it is too loose.")
    L.append("")
    L.append("## Zone A — real art, densest band (panel y "
             f"{ZONE_A[0]:+.1f} .. {ZONE_A[1]:+.1f})")
    L.append("")
    L.append(f"{len(inA)} of the panel's {len(cuts['webs'])} steel ribbons, including the worst "
             f"run on the panel. Also carries the y {-13.208:+.3f} pilot row — check pilot-to-art "
             f"edge quality and drill one to final size.")
    L.append("")
    L.append("| run | thick | panel (x, y) | coupon (x, y) | result |")
    L.append("|---|---|---|---|---|")
    for r in sorted(inA, key=lambda z: -z["len"]):
        L.append(f"| {r['len']:.3f} | {r['thick']:.4f} | ({r['x']:+.3f}, {r['y']:+.3f}) "
                 f"| ({r['x']:+.3f}, {r['y'] + lay['A_dy']:+.3f}) | |")
    L.append("")
    L.append("## Zone B — real art, worst cut-away ribbon (panel y "
             f"{ZONE_B[0]:+.1f} .. {ZONE_B[1]:+.1f})")
    L.append("")
    L.append("| run | width | panel (x, y) | coupon (x, y) | result |")
    L.append("|---|---|---|---|---|")
    for r in sorted(inB, key=lambda z: -z["len"]):
        L.append(f"| {r['len']:.3f} | {r['thick']:.4f} | ({r['x']:+.3f}, {r['y']:+.3f}) "
                 f"| ({r['x']:+.3f}, {r['y'] + lay['B_dy']:+.3f}) | |")
    L.append("")
    L.append("## Acceptance — measure, don't eyeball")
    L.append("")
    L.append(f"1. **Measured kerf.** Caliper a ladder SLOT (drawn {SLOT:.3f}) and a surviving")
    L.append(f"   WEB (drawn width, table above). With normal comp the finished size matches")
    L.append(f"   the drawing only when the kerf set in CAM equals the real kerf; if the real")
    L.append(f"   kerf is wider, slots come out wide and webs come out narrow by the same")
    L.append(f"   amount. So: real kerf = {ba.PLASMA_KERF:.3f} + (slot_measured - {SLOT:.3f}).")
    L.append(f"   The design assumes **{ba.PLASMA_KERF:.3f}\"**, which sets MIN_SLIVER (2x kerf),")
    L.append("   the ladder floor, the pilot-size check and every post-kerf web figure — so if")
    L.append("   this comes back materially different, `PLASMA_KERF` changes and the panel")
    L.append("   gets re-checked before cutting. NOTE: a consumable's stated orifice (e.g.")
    L.append("   0.8 mm) is NOT the kerf — the arc flares, so cut width runs wider, typically")
    L.append("   1.5-2x the bore. Measure, don't read it off the box.")
    L.append("2. **Ladder survival** per cell, table above.")
    L.append("3. **Flatness across the WHOLE coupon** — straightedge + feeler, record the")
    L.append("   worst gap and where. This is the one that scales to the panel: what kills")
    L.append("   the assembly is the face not seating on the frame, not an ugly cut.")
    L.append("4. **Local curl** at each surviving thin feature — a web can survive and still")
    L.append("   stand proud.")
    L.append("5. **Dross / tags** on the thin features, and whether they clean up without")
    L.append("   eating the feature.")
    L.append("6. **Detail loss** — compare zone A and B against the DXF. Tips will round;")
    L.append("   record how much, because that is what the customer sees.")
    L.append("")
    L.append("## What this coupon cannot tell you")
    L.append("")
    L.append(f"Cumulative distortion over {ba.H:.3f}\". A {lay['total_h']:.1f}\" piece cannot "
             f"reproduce the bow of a full panel. The coupon bounds the local question — do "
             f"these features survive, and where is the limit. Whole-panel flatness is "
             f"answered only by the panel, and the lever there is cut ordering in the dense "
             f"band so adjacent contours are not run consecutively.")
    L.append("")
    L.append("## Result")
    L.append("")
    L.append("- Tip hours at cut: ______   Date: ______   Cut by: ______")
    L.append(f"- Measured limit (longest surviving run): ______  vs gate {ba.MAX_THIN_RUN:.3f}")
    L.append("- `MAX_THIN_RUN` action: unchanged / raise to ______ / lower to ______")
    L.append("- Panel released to cut: yes / no")
    return "\n".join(L) + "\n"


def main():
    print(f"Bonebrake artwork cut coupon — Rev {ba.REV}")
    art = ba.artwork_face()
    if art is None:
        sys.exit("no artwork found")
    sk, lay = build(art)
    rows, cuts, inA, inB = checks(sk, lay, art)
    print("VALIDATION:")
    ok = True
    for name, passed, detail in rows:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        ok = ok and passed
    if not ok:
        print("\nFAILED checks — nothing written.")
        sys.exit(1)

    ba.OUT_DIR.mkdir(parents=True, exist_ok=True)
    ex = ExportDXF(unit=Unit.IN)
    ex.add_shape(sk)
    ex.write(str(OUT_DXF))
    # Repair first, THEN layer: a spline re-emitted as a polyline by the repair
    # would otherwise land back on layer 0 and miss the split.
    for p0, p1 in ba.repair_degenerate_splines(OUT_DXF):
        print(f"  repaired degenerate spline ({p0[0]:+.4f},{p0[1]:+.4f}) -> "
              f"({p1[0]:+.4f},{p1[1]:+.4f}) — re-emitted as polyline")
    tally = ba.layer_split_dxf(OUT_DXF)
    print(f"  layers: PILOTS {tally['PILOTS']} entities, CUTS {tally['CUTS']}")
    print(f"\nwrote {OUT_DXF.name}")
    OUT_SHEET.write_text(sheet(lay, cuts, inA, inB))
    print(f"wrote {OUT_SHEET.name}")
    print(f"\nblank {COUPON_W:.3f} x {lay['total_h']:.3f}  "
          f"({len(LADDER_W) * len(LADDER_L)} ladder cells, "
          f"{len(inA)} steel + {len(inB)} art ribbons of real geometry)")


if __name__ == "__main__":
    main()
