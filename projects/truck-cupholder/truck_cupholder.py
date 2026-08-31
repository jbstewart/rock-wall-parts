"""Truck cup holder — two-piece replacement insert per BRIEF.md.

Base (two identical interlocking halves, stays snapped under the seat's
embedded plate) + two identical twist-lock collars that support a 30 oz
tumbler at its full taper-top diameter and lift off so the platform can
fold for a third passenger.

Outputs: STEP assembly (named/colored components incl. reference cups),
print STEPs for the base half and collar (qty 2 each), fit-test coupon
STEPs (always emitted, derived from the real geometry), build sheet,
check report. All generation checks must pass or nothing is written.

Run:  ../../.venv/bin/python truck_cupholder.py
"""

import sys
from math import cos, radians, sin
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from build123d import (  # noqa: E402
    Box,
    Circle,
    Color,
    Compound,
    Cone,
    Cylinder,
    Plane,
    Polygon,
    Pos,
    Rot,
    export_step,
    extrude,
)

# --------------------------------------------------------------- PARAMETERS
# All inches; STEP exports scale x25.4 via place(). z=0 is the flange seat
# (top of upholstery), +z up, origin centered between the two bores.

REV = "A"

# Seat recess (SilveradoCupHolder Drawing.pdf + corrected worksheet)
BORE_CC = 3.75          # bore / recess circle centers
HOLE_D = 7.71 - BORE_CC  # 3.96 — recess & plate opening circle diameter
RECESS_DEPTH = 0.75
POCKET_W = 1.0          # 4 side clip pockets in the foam, below the plate
POCKET_OUT = 0.38       # pocket extends this far radially past the hole edge
POCKET_BELOW_PLATE = 0.5
FABRIC_L, FABRIC_W = 7.75, 4.0
LEDGE = 0.50            # flange seat -> plate UNDERSIDE (Brian, corrected 2026-08-30)
FOLD_LIMIT = 1.25       # base may stand at most this far above the fabric

# Cup — 30 oz tumbler, both bores (worksheet §5)
CUP_BASE_D = 2.8
CUP_TAPER_TOP_D = 3.5
CUP_TAPER_H = 3.45
CUP_RIM_D = 4.0         # at the rim (measured 2026-08-30)
CUP_H = 8.0             # rim height above cup bottom (measured 2026-08-30)
# NOTE: two Ø4.0 rims at 3.75 c-c overlap by 0.25 — two of these tumblers only
# coexist leaned apart (seat geometry, same for OEM). Checks scope cup-to-cup
# clearance to the collar support zone, where the design is responsible.

# Base
FLANGE_T = 0.132
FLANGE_R = 2.25         # figure-8 of these circles = 8.25 x 4.5 flange
PLUG_R = HOLE_D / 2 - 0.03   # 1.95 — radial clearance into the recess/plate opening
PLUG_BOTTOM = -0.70     # recess floor is -0.75
FLOOR_Z = -0.55         # cup rest floor (top surface) inside each well
WELL_R = 1.675          # well bore; collar skirt drops inside this
DRAIN_R = 0.125

# Snap clips (4) — engage under the plate, 45-deg-ish ramps both ways
CLIP_CC = 3.625         # hook centers; check proves fit for both measured pocket c-c (3.5 & 3.75)
CLIP_W = 0.70
CLIP_T = 0.065          # tongue thickness (~4 perimeters of a 0.4 nozzle)
CLIP_GAP = 0.06         # window side/back gaps around the tongue
PLATE_CLR = 0.03        # hook top sits this far below the plate underside
HOOK_ENG = 0.08         # radial bite past the plate opening edge
HOOK_TOP_Z = -(LEDGE + PLATE_CLR)      # -0.53
HOOK_TIP_Z = HOOK_TOP_Z - 0.12         # -0.65 (back-ramp ~50 deg -> removable)
TONGUE_BOT = -0.72                     # steeper lead-in below the tip
HOOK_TIP_R = HOLE_D / 2 + HOOK_ENG     # 2.06 from well center
INSERT_CLR = 0.015      # hook must retract to hole radius minus this to pass the plate
PETG_STRAIN_LIMIT = 0.035  # momentary flex during snap-in (coupon validates)

# Bayonet (collar frame: waist scallop faces +x, i.e. azimuth 0)
LUG_AZ = (135, 315)     # locked lug centers
TWIST = 25              # insert at LUG_AZ + TWIST (outboard), twist toward waist to lock
LUG_ARC = 20
ENTRY_ARC = 24
SKIRT_RO = 1.65
SKIRT_Z0 = -0.42
LUG_RO = 1.80
LUG_Z = (-0.42, -0.27)
CH_Z = (-0.45, -0.245)  # horizontal channel (lug track) under the flange
CH_RI, CH_RO = 1.58, 1.83
COLLAR_SEAT = FLANGE_T  # collar seats on the flange top

# Collar
COL_TOP = 3.132         # supports the cup right above its taper top (z 2.90)
RING_RO = 1.85          # base ring hides the entry slots cut through the flange
RING_T = 0.10
CONE_RO_B, CONE_RO_T = 1.655, 1.95
CONE_RI_B, CONE_RI_T = 1.53, 1.85    # inner taper, SKIRT_Z0 -> COL_TOP
SCALLOP_R = 2.02        # neighbor-envelope trim; guarantees collar-collar clearance

# Printer — Creality CR-6 SE (confirmed 2026-08-30); one-piece base fits the bed
BED_MM = 235.0
ZMAX_MM = 250.0
IN = 25.4

OUT_DIR = Path(__file__).parent / "output"
COUPON_DIR = OUT_DIR / "coupon"
BASENAME = "truck-cupholder"
REV_TAG = f"rev{REV}"
BRIEF_PATH = Path(__file__).parent / "BRIEF.md"


# --------------------------------------------------------------- HELPERS


COLORS = {
    "base": Color(0.15, 0.15, 0.15),
    "collar": Color(0.90, 0.45, 0.10),
    "cup": Color(0.85, 0.10, 0.10),
}


def place(part, label: str, x=0.0, y=0.0, z=0.0):
    """Scale an origin-frame inch part to mm and place it (house convention;
    scale() also serves as the copy so repeated placements keep their labels)."""
    shaped = part.scale(IN)
    located = Pos(x * IN, y * IN, z * IN) * shaped
    located.label = label
    color = COLORS.get(label.rstrip("0123456789-LR"))
    if color is not None:
        located.color = color
    return located


def sector(r1: float, r2: float, a1: float, a2: float, z1: float, z2: float):
    """Annular-sector prism, azimuth a1->a2 CCW from +x, degrees (span < 180)."""
    ring = Circle(r2) - Circle(r1)
    reach = 10.0
    tri = Polygon(
        (0, 0),
        (reach * cos(radians(a1)), reach * sin(radians(a1))),
        (reach * cos(radians(a2)), reach * sin(radians(a2))),
    )
    return Pos(0, 0, z1) * extrude(ring & tri, z2 - z1)


def figure8(r: float):
    return Pos(-BORE_CC / 2, 0) * Circle(r) + Pos(BORE_CC / 2, 0) * Circle(r)


# --------------------------------------------------------------- BASE

# Tongue face is the chord plane whose corners land ON the plug wall — flat
# tongue, nothing proud of the plug except the hook itself.
TONGUE_FACE_R = (PLUG_R**2 - (CLIP_W / 2) ** 2) ** 0.5  # 1.918


def clip_tongue():
    """One snap clip in local frame: centered on x, outward +y, hanging from
    the flange. Hook profile drawn in the YZ plane, extruded across the width."""
    leg_top = 0.12  # root buried in the flange for a solid fillet-free anchor
    leg = Pos(0, TONGUE_FACE_R - CLIP_T / 2, (leg_top + TONGUE_BOT) / 2) * Box(
        CLIP_W, CLIP_T, leg_top - TONGUE_BOT
    )
    hook_profile = Plane.YZ * Polygon(
        (TONGUE_FACE_R, HOOK_TOP_Z),
        (HOOK_TIP_R, HOOK_TIP_Z),
        (TONGUE_FACE_R, TONGUE_BOT),
    )
    # extrude() on a Plane.YZ sketch runs -X, not +X (bit us at Rev A: hooks
    # landed a full width sideways as floating solids) — shift +w/2 to center.
    hook = Pos(CLIP_W / 2, 0, 0) * extrude(hook_profile, CLIP_W)
    return leg + hook


def clip_window():
    """Wall cutout that frees the tongue to flex (local frame, +y side)."""
    w = CLIP_W + 2 * CLIP_GAP
    y_mid = (WELL_R - 0.09 + PLUG_R + 0.15) / 2
    depth = (PLUG_R + 0.15) - (WELL_R - 0.09)
    return Pos(0, y_mid, (0.0 + (TONGUE_BOT - 0.06)) / 2) * Box(
        w, depth, 0.0 - (TONGUE_BOT - 0.06)
    )


def bayonet_cuts_left():
    """Entry slots + lug channels for the LEFT well, in well-local coords.
    Lock at LUG_AZ (twist CW from outboard); entries live near the oval end,
    clear of the clips (az ~90/270) and the waist joint (az 0)."""
    cuts = []
    for lug_az in LUG_AZ:
        entry_az = lug_az + TWIST
        cuts.append(
            sector(CH_RI, CH_RO, entry_az - ENTRY_ARC / 2, entry_az + ENTRY_ARC / 2,
                   CH_Z[0], FLANGE_T + 0.1)
        )
        cuts.append(
            sector(CH_RI, CH_RO, lug_az - LUG_ARC / 2 - 4, entry_az + ENTRY_ARC / 2,
                   CH_Z[0], CH_Z[1])
        )
    out = cuts[0]
    for c in cuts[1:]:
        out += c
    return out


def build_base_full():
    """The whole base, unsplit, in the global frame (wells at +-BORE_CC/2)."""
    flange = extrude(figure8(FLANGE_R), FLANGE_T)
    plug = Pos(0, 0, PLUG_BOTTOM) * extrude(figure8(PLUG_R), -PLUG_BOTTOM)
    base = flange + plug

    for sx in (-1, 1):
        well = Pos(sx * BORE_CC / 2, 0, FLOOR_Z) * extrude(Circle(WELL_R), 1.0)
        drain = Pos(sx * BORE_CC / 2, 0, -0.9) * extrude(Circle(DRAIN_R), 0.5)
        base = base - well - drain

    slots = bayonet_cuts_left()
    base -= Pos(-BORE_CC / 2, 0, 0) * slots
    base -= Pos(BORE_CC / 2, 0, 0) * Rot(0, 0, 180) * slots

    tongue, window = clip_tongue(), clip_window()
    for gx in (-CLIP_CC / 2, CLIP_CC / 2):
        for ang in (0, 180):
            base -= Pos(gx, 0, 0) * Rot(0, 0, ang) * window
    for gx in (-CLIP_CC / 2, CLIP_CC / 2):
        for ang in (0, 180):
            base += Pos(gx, 0, 0) * Rot(0, 0, ang) * tongue
    return base


# --------------------------------------------------------------- COLLAR


def build_collar():
    """One collar in well-local frame, waist scallop facing +x. The same part
    rotated 180 deg serves the other well."""
    cone_h = COL_TOP - COLLAR_SEAT
    outer = Pos(0, 0, COLLAR_SEAT + cone_h / 2) * Cone(CONE_RO_B, CONE_RO_T, cone_h)
    ring = Pos(0, 0, COLLAR_SEAT + RING_T / 2) * Cylinder(RING_RO, RING_T)
    skirt_h = COLLAR_SEAT - SKIRT_Z0
    skirt = Pos(0, 0, SKIRT_Z0 + skirt_h / 2) * Cylinder(SKIRT_RO, skirt_h)
    collar = outer + ring + skirt
    for az in LUG_AZ:
        collar += sector(SKIRT_RO - 0.03, LUG_RO, az - LUG_ARC / 2, az + LUG_ARC / 2,
                         LUG_Z[0], LUG_Z[1])
    # inner taper: one continuous cone from below the skirt to above the top
    slope = (CONE_RI_T - CONE_RI_B) / (COL_TOP - SKIRT_Z0)
    z1, z2 = SKIRT_Z0 - 0.01, COL_TOP + 0.01
    r1, r2 = CONE_RI_B - 0.01 * slope, CONE_RI_T + 0.01 * slope
    inner = Pos(0, 0, (z1 + z2) / 2) * Cone(r1, r2, z2 - z1)
    collar -= inner
    scallop = Pos(BORE_CC, 0, 1.0) * Cylinder(SCALLOP_R, 9.0)
    return collar - scallop


def cup_radius(z: float) -> float:
    """Tumbler radius at height z (global frame, cup on the well floor)."""
    h = z - FLOOR_Z
    if h <= CUP_TAPER_H:
        return CUP_BASE_D / 2 + (CUP_TAPER_TOP_D - CUP_BASE_D) / 2 * h / CUP_TAPER_H
    frac = min(1.0, (h - CUP_TAPER_H) / (CUP_H - CUP_TAPER_H))
    return CUP_TAPER_TOP_D / 2 + (CUP_RIM_D - CUP_TAPER_TOP_D) / 2 * frac


def build_cup():
    """Reference 30 oz tumbler (base taper + flared body to the Ø4.0 rim)
    sitting on the well floor, in well-local frame."""
    taper = Pos(0, 0, FLOOR_Z + CUP_TAPER_H / 2) * Cone(
        CUP_BASE_D / 2, CUP_TAPER_TOP_D / 2, CUP_TAPER_H
    )
    body_h = CUP_H - CUP_TAPER_H
    body = Pos(0, 0, FLOOR_Z + CUP_TAPER_H + body_h / 2) * Cone(
        CUP_TAPER_TOP_D / 2, CUP_RIM_D / 2, body_h
    )
    return taper + body


# --------------------------------------------------------------- CHECKS


def isect_vol(a, b) -> float:
    try:
        common = a & b
    except Exception:
        return 0.0
    return getattr(common, "volume", 0.0) or 0.0


def bbox_xy_in(shape) -> tuple[float, float]:
    bb = shape.bounding_box()
    return bb.size.X, bb.size.Y


def run_checks(base_full, collar, cups_placed, collars_placed):
    deflect = HOOK_TIP_R - (HOLE_D / 2 - INSERT_CLR)
    hook_mid_z = (HOOK_TOP_Z + HOOK_TIP_Z) / 2
    strain = 1.5 * CLIP_T * deflect / hook_mid_z**2
    hook_lo, hook_hi = CLIP_CC / 2 - CLIP_W / 2, CLIP_CC / 2 + CLIP_W / 2
    pockets = {"drawing c-c 3.5": 3.5, "worksheet c-c 3.75": 3.75}
    pocket_fit = all(
        pcc / 2 - POCKET_W / 2 + 0.02 <= hook_lo and hook_hi <= pcc / 2 + POCKET_W / 2 - 0.02
        for pcc in pockets.values()
    )
    base_bb = base_full.bounding_box()
    col_bb = collar.bounding_box()
    col_xy = max(col_bb.size.X, col_bb.size.Y)
    base_top = base_bb.max.Z
    # the -X extrude bug (Rev A dev) left the hook detached; prove the tongue
    # is one connected solid living entirely inside the clip width
    tongue = clip_tongue()
    t_bb = tongue.bounding_box()
    tongue_ok = (len(tongue.solids()) == 1
                 and max(abs(t_bb.min.X), abs(t_bb.max.X)) <= CLIP_W / 2 + 1e-3)

    ri = lambda z: CONE_RI_B + (CONE_RI_T - CONE_RI_B) * (z - SKIRT_Z0) / (COL_TOP - SKIRT_Z0)
    clr_bot = ri(SKIRT_Z0) - cup_radius(SKIRT_Z0)
    clr_top = ri(COL_TOP) - cup_radius(COL_TOP)

    # pre-twist position: lugs sit in the entry slots (kernel-proves alignment)
    pre_l = Pos(-BORE_CC / 2, 0, 0) * Rot(0, 0, TWIST) * collar.scale(1.0)

    checks = [
        ("plug fits recess/plate opening", PLUG_R <= HOLE_D / 2 - 0.02,
         f"plug r {PLUG_R:.3f} <= hole r {HOLE_D / 2:.3f} - 0.02"),
        ("nothing below the recess floor", TONGUE_BOT >= -(RECESS_DEPTH - 0.02),
         f"lowest point {TONGUE_BOT:.2f} >= {-(RECESS_DEPTH - 0.02):.2f}"),
        ("base folds into the seatback", base_top <= FOLD_LIMIT,
         f"base stands {base_top:.3f} above fabric <= {FOLD_LIMIT}"),
        ("flange covers the fabric opening", 2 * FLANGE_R >= FABRIC_W + 0.4
         and BORE_CC + 2 * FLANGE_R >= FABRIC_L + 0.4,
         f"flange 8-fig {BORE_CC + 2 * FLANGE_R:.2f} x {2 * FLANGE_R:.2f} vs fabric {FABRIC_L} x {FABRIC_W} + 0.2/side"),
        ("hook engages under the plate", 0.02 <= -(HOOK_TOP_Z + LEDGE) <= 0.08,
         f"hook top {HOOK_TOP_Z:.2f}, plate underside {-LEDGE:.2f} (clr {-(HOOK_TOP_Z + LEDGE):.3f})"),
        ("hook bite is real but insertable", 0.06 <= HOOK_ENG <= POCKET_OUT - 0.02,
         f"bite {HOOK_ENG:.2f} past plate edge, pocket allows {POCKET_OUT - 0.02:.2f}"),
        ("hooks land in pockets under BOTH measured spacings", pocket_fit,
         f"hook span {hook_lo:.3f}..{hook_hi:.3f} in 1.0-wide pockets at c-c 3.5 AND 3.75"),
        ("hook clears pocket floor", TONGUE_BOT >= -(LEDGE + POCKET_BELOW_PLATE) + 0.05,
         f"tongue bottom {TONGUE_BOT:.2f} >= pocket floor {-(LEDGE + POCKET_BELOW_PLATE):.2f} + 0.05"),
        ("snap-in flex within PETG limit", strain <= PETG_STRAIN_LIMIT,
         f"strain {strain * 100:.2f}% <= {PETG_STRAIN_LIMIT * 100:.1f}% (deflect {deflect:.3f} over L {-hook_mid_z:.2f})"),
        ("collar supports the cup above its taper", COL_TOP >= FLOOR_Z + CUP_TAPER_H + 0.2,
         f"collar top {COL_TOP:.2f} >= taper top {FLOOR_Z + CUP_TAPER_H:.2f} + 0.2"),
        ("cup clearance in collar (bottom / top)", clr_bot >= 0.05 and clr_top >= 0.05,
         f"radial clr {clr_bot:.3f} / {clr_top:.3f} >= 0.05"),
        ("cups clear each other through the collar zone",
         BORE_CC - 2 * cup_radius(COL_TOP) >= 0.15,
         f"gap {BORE_CC - 2 * cup_radius(COL_TOP):.2f} at collar top; NOTE Ø{CUP_RIM_D} rims "
         f"overlap {2 * cup_radius(FLOOR_Z + CUP_H) - BORE_CC:.2f} higher up — seat geometry, cups lean apart"),
        ("collars never touch each other (kernel)",
         isect_vol(*collars_placed) < 1e-4, "locked positions, boolean intersection"),
        ("collar never touches the base, locked (kernel)",
         isect_vol(collars_placed[0], base_full) < 1e-4
         and isect_vol(collars_placed[1], base_full) < 1e-4,
         "lugs ride inside the channel voids"),
        ("collar drops into the entry slots, pre-twist (kernel)",
         isect_vol(pre_l, base_full) < 1e-4,
         f"collar rotated +{TWIST} deg still clears the base"),
        ("cups touch neither collar nor base (kernel)",
         all(isect_vol(c, s) < 1e-4 for c in cups_placed
             for s in (collars_placed[0], collars_placed[1], base_full)),
         "reference cup solids vs everything"),
        ("clip tongue is one solid, inside the clip width", tongue_ok,
         f"{len(tongue.solids())} solid(s), x span ±{max(abs(t_bb.min.X), abs(t_bb.max.X)):.3f}"),
        ("one-piece base fits the CR-6 bed",
         max(base_bb.size.X, base_bb.size.Y) * IN <= BED_MM - 4,
         f"base bbox {base_bb.size.X * IN:.0f} x {base_bb.size.Y * IN:.0f} mm <= {BED_MM:.0f}-4"),
        ("collar fits the bed and Z", col_xy * IN <= BED_MM - 4
         and col_bb.size.Z * IN <= ZMAX_MM - 5,
         f"collar {col_bb.size.X * IN:.0f} x {col_bb.size.Y * IN:.0f} x {col_bb.size.Z * IN:.0f} mm"),
        ("lug track has outer skin left in the plug wall", PLUG_R - CH_RO >= 0.10,
         f"skin {PLUG_R - CH_RO:.2f} >= 0.10"),
        ("BRIEF current revision matches script REV",
         f"Current revision: **{REV}**" in BRIEF_PATH.read_text(),
         f'BRIEF.md contains "Current revision: **{REV}**"'),
    ]
    return checks


# --------------------------------------------------------------- BUILD SHEET


def write_buildsheet(out_path: Path) -> Path:
    text = f"""# Truck Cup Holder — Build Sheet  (Rev {REV})

Generated by truck_cupholder.py at Rev {REV} — regenerate, don't hand-edit.

## Parts to print (PETG, 0.4 nozzle, CR-6 SE)

| File | Qty | Orientation | Notes |
|---|---|---|---|
| {BASENAME}-base-{REV_TAG}.step | **1** | flange face DOWN | ~211 mm long — one piece; clips grow upward, no supports |
| {BASENAME}-collar-{REV_TAG}.step | **2** | wide (top) end DOWN | identical collars; skirt+lugs print last |

Slicer: import STEP directly (it's mm). ≥4 perimeters (the 0.065" clip tongues must be
solid walls, not infill), 30–40% infill, PETG temps. No supports needed in the stated
orientations; the small lug overhangs bridge fine.

## Coupons — print and fit these BEFORE the full parts

| File | Tests |
|---|---|
| coupon/{BASENAME}-clip-coupon-{REV_TAG}.step | one real clip + flange strip: snap it into a truck pocket — engagement, removal force, PETG layer survival |
| coupon/{BASENAME}-well-coupon-{REV_TAG}.step | one full well ring (clips + bayonet slots) |
| coupon/{BASENAME}-collar-coupon-{REV_TAG}.step | shortened collar: twist-lock into the well coupon, drop the cup base in |

If the clip coupon snaps (the part, not the click): thicken CLIP_T or shrink HOOK_ENG
in the script and regenerate — do not hand-tune prints.

## Assembly & use

1. Press the base into the platform recess until all four clips click under the plate.
   The flange should sit flat on the fabric. It stays there permanently
   (firm straight pull removes it if ever needed — the hooks are back-ramped).
2. Collars: lugs drop into the two slots near the OUTBOARD end of each well,
   then twist {TWIST} deg toward the seat center until the stop. Same part both
   sides — the scalloped side always faces the other cup.
3. Fold-up for a third passenger: twist each collar back, lift, toss in the door
   pocket, fold the platform. Base stays in (stands only {FLANGE_T:.2f}" proud;
   fold limit is {FOLD_LIMIT}").
"""
    out_path.write_text(text)
    return out_path


# --------------------------------------------------------------- MAIN


def main() -> None:
    print(f"Truck cup holder — Rev {REV}")
    print("building geometry…")
    base_full = build_base_full()
    collar = build_collar()
    cup = build_cup()

    collar_l = Pos(-BORE_CC / 2, 0, 0) * collar.scale(1.0)
    collar_r = Pos(BORE_CC / 2, 0, 0) * Rot(0, 0, 180) * collar.scale(1.0)
    cup_l = Pos(-BORE_CC / 2, 0, 0) * cup.scale(1.0)
    cup_r = Pos(BORE_CC / 2, 0, 0) * cup.scale(1.0)

    checks = run_checks(base_full, collar, (cup_l, cup_r), (collar_l, collar_r))
    print("VALIDATION:")
    ok = True
    for name, passed, detail in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        ok = ok and passed
    if not ok:
        print("\nFAILED checks — no geometry written.")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    COUPON_DIR.mkdir(parents=True, exist_ok=True)

    # assembly STEP — everything in situ, cups included as references
    parts = [
        place(base_full, "base"),
        place(collar, "collar-L", x=-BORE_CC / 2),
        place(Rot(0, 0, 180) * collar, "collar-R", x=BORE_CC / 2),
        place(cup, "cup-L", x=-BORE_CC / 2),
        place(cup, "cup-R", x=BORE_CC / 2),
    ]
    asm = Compound(children=parts)
    asm.label = f"{BASENAME}-{REV_TAG}"
    asm_path = OUT_DIR / f"{BASENAME}-assembly-{REV_TAG}.step"
    export_step(asm, str(asm_path))
    print(f"wrote {asm_path.name}")

    # print STEPs (one file per unique part; qty in the build sheet)
    for shape, stem in ((base_full, "base"), (collar, "collar")):
        p = OUT_DIR / f"{BASENAME}-{stem}-{REV_TAG}.step"
        export_step(place(shape, stem), str(p))
        print(f"wrote {p.name}")

    # coupons — cut straight out of the real geometry
    clip_zone = Pos(CLIP_CC / 2, 1.80, -0.3) * Box(0.9, 1.0, 1.6)
    well_zone = Pos(-BORE_CC / 2, 0, 0) * Cylinder(2.12, 4.0)
    collar_zone = Pos(0, 0, 0.25) * Box(10, 10, 3.2)
    coupons = (
        (base_full & clip_zone, "clip-coupon"),
        (base_full & well_zone, "well-coupon"),
        (collar & collar_zone, "collar-coupon"),
    )
    for shape, stem in coupons:
        p = COUPON_DIR / f"{BASENAME}-{stem}-{REV_TAG}.step"
        export_step(place(shape, stem), str(p))
        print(f"wrote coupon/{p.name}")

    sheet = write_buildsheet(OUT_DIR / f"{BASENAME}-buildsheet-{REV_TAG}.md")
    print(f"wrote {sheet.name}")


if __name__ == "__main__":
    main()
