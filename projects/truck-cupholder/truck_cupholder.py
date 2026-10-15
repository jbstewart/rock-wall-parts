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
    Rectangle,
    Rot,
    export_step,
    export_stl,
    extrude,
)

# --------------------------------------------------------------- PARAMETERS
# All inches; STEP exports scale x25.4 via place(). z=0 is the flange seat
# (top of upholstery), +z up, origin centered between the two bores.

REV = "G"

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

# Snap clips (4) — engage under the plate, 45-deg-ish ramps both ways.
# Rev C: SEPARATE parts, printed flat (Casey's coupon snapped at the root —
# integral clips print with layer seams ACROSS the leg; flat-printed clips
# carry the bend along continuous perimeter lines). T-head drops into a pocket
# through the flange and bears on the plug wall: pull-out load seats the head
# DEEPER. Light press fit; a drop of CA is cheap insurance (build sheet).
CLIP_CC = 3.625         # hook centers; check proves fit for both measured pocket c-c (3.5 & 3.75)
CLIP_W = 0.60           # Rev B: narrowed from 0.70 so the hook's outer corner stays
                        # close to the stadium's straight wall (corner curve costs deflection)
HEAD_W = 0.90           # clip T-head bar
HEAD_DEPTH = 0.23       # radial (y) depth of the head
POCKET_CLR = 0.01       # pocket oversize per side around the head
CLIP_T = 0.065          # tongue thickness (~4 perimeters of a 0.4 nozzle)
CLIP_GAP = 0.06         # window side/back gaps around the tongue
HOOK_ENG = 0.08         # radial bite past the plate opening edge
TONGUE_BOT = -0.72      # lead-in ramp runs from the tip back to the face here
HOOK_TIP_R = HOLE_D / 2 + HOOK_ENG     # 2.06 from well center
INSERT_CLR = 0.015      # hook must retract to hole radius minus this to pass the plate
# Rev D: the 45-deg back-ramp let the plate corner land partway down the slope —
# measured 11/16 to the tip vs the 1/2 ledge depth, ~1/16+ of slack (Brian).
# Now a SHALLOW back-ramp is aimed so the bearing point AT THE PLATE CORNER
# sits exactly LEDGE below the flange seat (+SNUG_ADJUST): snug, and a firm
# pull still cams it off for removal.
RAMP_SLOPE = 0.4        # dz per dr of the back-ramp (~22 deg from horizontal)
SNUG_ADJUST = 0.000     # + loosens, - preloads; THE field-tuning knob after a test fit
PETG_STRAIN_LIMIT = 0.045  # in-plane limit — clips print FLAT (Rev C); the old
                           # 0.035 guarded the across-layer direction

# Bayonet (collar frame: waist scallop faces +x, i.e. azimuth 0)
LUG_AZ = (135, 315)     # locked lug centers
TWIST = 35              # insert at LUG_AZ + TWIST (outboard), twist toward waist to lock
                        # Rev F: 25 -> 35 deg = ~1.04" of lug travel (Brian: longer,
                        # more secure wrap; lugs unchanged, entries rotate to suit)
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
COL_CONE_TOP = 3.132    # inner/outer taper ends here (right above the cup's taper top)
COL_STRAIGHT = 0.875    # Rev F straight extension (Brian: 7/8 headroom before the
                        # cup's next section; bore goes STRAIGHT, not tapered)
COL_TOP = COL_CONE_TOP + COL_STRAIGHT
# Rev F grip ribs — the coupon fooled us: the loose cone let the cup wedge high
# and feel snug, but bottomed on the well floor the bore had ~3/32+ radial slop
# (Brian measured). Six internal ribs whose tips FOLLOW the cup profile at a
# constant gap; RIB_CLR is THE fit knob (cone clearance stays drop-in loose).
RIB_AZ = (45, 90, 135, 225, 270, 315)  # C2-symmetric, all >= 45 deg from the
                        # az-0 notch (a 30-deg fin would get sliced by it)
RIB_W = 0.12
RIB_CLR = 0.015         # radial rib-tip-to-cup gap
RIB_Z0 = 0.25           # ribs start above the well-floor entry region
RING_RO = 1.85          # base ring hides the entry slots cut through the flange
RING_T = 0.10
WALL = 0.14             # Rev E: beefed from 0.10 (Casey); grows OUTWARD, cup ID untouched
CONE_RI_B, CONE_RI_T = 1.53, 1.85    # inner taper, SKIRT_Z0 -> COL_TOP
CONE_RO_B, CONE_RO_T = CONE_RI_B + WALL, CONE_RI_T + WALL
# Rev E: the neighbor-clearance scallop (an envelope-trim artifact that read as
# a print accident — Brian) becomes a DELIBERATE U-shaped relief notch through
# the wall, facing the other cup. It carries all waist clearance for the
# beefed wall; kernel checks prove a locked pair never touch and a second
# collar drops in beside a locked one.
NOTCH_W = 1.70          # chord width of the U
NOTCH_BOT = 1.55        # lowest point of the U (round bottom, r = NOTCH_W/2)

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
    "clip": Color(0.45, 0.45, 0.50),
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


def stadium(r: float):
    """Two circles joined by a full-height rectangle — the recess is a STADIUM,
    not a figure-8 (Rev B: Brian's drawing; a bare circle-union pinches to ~1"
    at the waist and left the recess visible mid-span on both sides)."""
    return (
        Rectangle(BORE_CC, 2 * r)
        + Pos(-BORE_CC / 2, 0) * Circle(r)
        + Pos(BORE_CC / 2, 0) * Circle(r)
    )


# --------------------------------------------------------------- BASE

# The clip's outer corner reaches past the stadium's straight section into the
# end-circle curve; the tongue face sits flush with the wall at that corner
# (slightly recessed along the straight run), so nothing but the hook is proud.
CLIP_CORNER_OFF = max(0.0, CLIP_CC / 2 + CLIP_W / 2 - BORE_CC / 2)
TONGUE_FACE_R = (PLUG_R**2 - CLIP_CORNER_OFF**2) ** 0.5
# plate opening edge at the clip's worst (outer) corner, and the hook-ramp z's
# solved so the ramp crosses the plate corner at exactly LEDGE (+SNUG_ADJUST)
PLATE_EDGE_MIN = (HOLE_D**2 / 4 - CLIP_CORNER_OFF**2) ** 0.5
HOOK_ROOT_Z = -LEDGE + (PLATE_EDGE_MIN - TONGUE_FACE_R) * RAMP_SLOPE + SNUG_ADJUST
HOOK_TIP_Z = HOOK_ROOT_Z - (HOOK_TIP_R - TONGUE_FACE_R) * RAMP_SLOPE


def clip_part():
    """One snap clip as a SEPARATE part (Rev C), modeled installed on the +y
    side: T-head flush in the flange pocket, leg + hook hanging through the
    wall slot. PRINT FLAT (lying on its side) — that runs the layer lines
    root-to-hook, the direction the integral Rev B clip snapped across."""
    head_h = FLANGE_T - 0.002  # sits 2 thou below the flange top
    head = Pos(0, TONGUE_FACE_R - HEAD_DEPTH / 2, head_h / 2) * Box(
        HEAD_W, HEAD_DEPTH, head_h
    )
    leg_top = 0.10  # fused up into the head
    leg = Pos(0, TONGUE_FACE_R - CLIP_T / 2, (leg_top + TONGUE_BOT) / 2) * Box(
        CLIP_W, CLIP_T, leg_top - TONGUE_BOT
    )
    hook_profile = Plane.YZ * Polygon(
        (TONGUE_FACE_R, HOOK_ROOT_Z),
        (HOOK_TIP_R, HOOK_TIP_Z),
        (TONGUE_FACE_R, TONGUE_BOT),
    )
    # extrude() on a Plane.YZ sketch runs -X, not +X (bit us at Rev A: hooks
    # landed a full width sideways as floating solids) — shift +w/2 to center.
    hook = Pos(CLIP_W / 2, 0, 0) * extrude(hook_profile, CLIP_W)
    return head + leg + hook


def clip_cuts():
    """Base cutouts at one clip position (+y side): head pocket through the
    flange (floor = plug-wall top, the bearing surface) and the wall slot the
    leg flexes in."""
    pocket = Pos(0, TONGUE_FACE_R - HEAD_DEPTH / 2, 0.15) * Box(
        HEAD_W + 2 * POCKET_CLR, HEAD_DEPTH + 2 * POCKET_CLR, 0.30
    )
    # Rev G: the slot runs THROUGH the flange — at Rev F it stopped at the
    # flange underside, leaving only the 0.134 pocket/slot overlap as the way
    # in, and the 0.189-deep hook could not pass (Brian's clip snapped trying).
    # Leaves a small open slot outboard of each head; doubles as drainage.
    slot_y1, slot_y2 = TONGUE_FACE_R - CLIP_T - CLIP_GAP, HOOK_TIP_R + 0.09
    slot_top = FLANGE_T + 0.07
    slot = Pos(0, (slot_y1 + slot_y2) / 2, (slot_top + TONGUE_BOT - 0.06) / 2) * Box(
        CLIP_W + 2 * CLIP_GAP, slot_y2 - slot_y1, slot_top - (TONGUE_BOT - 0.06)
    )
    return pocket + slot


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
    """The whole base, one piece, in the global frame (wells at +-BORE_CC/2)."""
    flange = extrude(stadium(FLANGE_R), FLANGE_T)
    plug = Pos(0, 0, PLUG_BOTTOM) * extrude(stadium(PLUG_R), -PLUG_BOTTOM)
    base = flange + plug

    for sx in (-1, 1):
        well = Pos(sx * BORE_CC / 2, 0, FLOOR_Z) * extrude(Circle(WELL_R), 1.0)
        drain = Pos(sx * BORE_CC / 2, 0, -0.9) * extrude(Circle(DRAIN_R), 0.5)
        base = base - well - drain

    slots = bayonet_cuts_left()
    base -= Pos(-BORE_CC / 2, 0, 0) * slots
    base -= Pos(BORE_CC / 2, 0, 0) * Rot(0, 0, 180) * slots

    cuts = clip_cuts()
    for gx in (-CLIP_CC / 2, CLIP_CC / 2):
        for ang in (0, 180):
            base -= Pos(gx, 0, 0) * Rot(0, 0, ang) * cuts
    return base


def place_clips(clip):
    """The four clip parts in their installed positions."""
    return [
        Pos(gx, 0, 0) * Rot(0, 0, ang) * clip.scale(1.0)
        for gx in (-CLIP_CC / 2, CLIP_CC / 2)
        for ang in (0, 180)
    ]


# --------------------------------------------------------------- COLLAR


def build_collar():
    """One collar in well-local frame, waist relief notch facing +x. The same
    part rotated 180 deg serves the other well."""
    cone_h = COL_CONE_TOP - COLLAR_SEAT
    slope_o = (CONE_RO_T - CONE_RO_B) / cone_h
    outer = Pos(0, 0, COLLAR_SEAT + cone_h / 2) * Cone(CONE_RO_B, CONE_RO_T, cone_h)
    outer += Pos(0, 0, COL_CONE_TOP + COL_STRAIGHT / 2) * Cylinder(CONE_RO_T, COL_STRAIGHT)
    ring = Pos(0, 0, COLLAR_SEAT + RING_T / 2) * Cylinder(RING_RO, RING_T)
    # Rev C (Casey): 45-deg chamfer blends the ring top into the cone so the
    # upside-down print has no flat overhang ledge — no supports.
    collar = outer + ring
    ring_top = COLLAR_SEAT + RING_T
    # chamfer cone: from ring OD at ring_top, 45 deg up-inward until it meets the body
    ch_height = 0.19
    ring_ch = Pos(0, 0, ring_top + ch_height / 2) * Cone(
        RING_RO, CONE_RO_B + slope_o * (ring_top + ch_height - COLLAR_SEAT) + 0.005,
        ch_height,
    )
    collar += ring_ch
    skirt_h = COLLAR_SEAT - SKIRT_Z0
    skirt = Pos(0, 0, SKIRT_Z0 + skirt_h / 2) * Cylinder(SKIRT_RO, skirt_h)
    collar += skirt
    # Rev C (Casey): lugs are 45-deg wedges — full protrusion at the bottom,
    # flush with the skirt at the top — so the upside-down print (lugs last)
    # never overhangs. The bayonet channel ceiling bears on the top edge at
    # the skirt root; retention loads there are small.
    lug_wedge = Pos(0, 0, (LUG_Z[0] + LUG_Z[1]) / 2) * Cone(
        LUG_RO + 0.01, SKIRT_RO, LUG_Z[1] - LUG_Z[0]
    )
    for az in LUG_AZ:
        lug = sector(SKIRT_RO - 0.03, LUG_RO, az - LUG_ARC / 2, az + LUG_ARC / 2,
                     LUG_Z[0], LUG_Z[1])
        collar += lug & lug_wedge
    # inner: cone up to COL_CONE_TOP, then STRAIGHT bore to the top (Rev F)
    slope = (CONE_RI_T - CONE_RI_B) / (COL_CONE_TOP - SKIRT_Z0)
    z1 = SKIRT_Z0 - 0.01
    r1 = CONE_RI_B - 0.01 * slope
    inner = Pos(0, 0, (z1 + COL_CONE_TOP) / 2) * Cone(r1, CONE_RI_T, COL_CONE_TOP - z1)
    inner += Pos(0, 0, (COL_CONE_TOP - 0.02 + COL_TOP + 0.01) / 2) * Cylinder(
        CONE_RI_T, COL_TOP + 0.01 - (COL_CONE_TOP - 0.02)
    )
    collar -= inner
    # grip ribs: fins clipped to the body envelope, tips carved by the grown cup
    fins = None
    for az in RIB_AZ:
        fin = Rot(0, 0, az) * Pos(1.72, 0, (RIB_Z0 + COL_TOP - 0.05) / 2) * Box(
            0.76, RIB_W, COL_TOP - 0.05 - RIB_Z0
        )
        fins = fin if fins is None else fins + fin
    body_envelope = outer + skirt
    collar += (fins & body_envelope) - build_cup(RIB_CLR)
    # U-notch: straight sides + full-round bottom, cut radially through the
    # wall toward the neighbor (+x). Prism reaches x 1.15..2.55 — through the
    # near wall only, the far wall is at -x.
    zb = NOTCH_BOT + NOTCH_W / 2
    ztop = COL_TOP + 0.3
    notch = Pos(1.85, 0, (zb + ztop) / 2) * Box(1.4, NOTCH_W, ztop - zb)
    notch += Pos(1.85, 0, zb) * Rot(0, 90, 0) * Cylinder(NOTCH_W / 2, 1.4)
    return collar - notch


def cup_radius(z: float) -> float:
    """Tumbler radius at height z (global frame, cup on the well floor)."""
    h = z - FLOOR_Z
    if h <= CUP_TAPER_H:
        return CUP_BASE_D / 2 + (CUP_TAPER_TOP_D - CUP_BASE_D) / 2 * h / CUP_TAPER_H
    frac = min(1.0, (h - CUP_TAPER_H) / (CUP_H - CUP_TAPER_H))
    return CUP_TAPER_TOP_D / 2 + (CUP_RIM_D - CUP_TAPER_TOP_D) / 2 * frac


def build_cup(grow: float = 0.0):
    """Reference 30 oz tumbler (base taper + flared body to the Ø4.0 rim)
    sitting on the well floor, in well-local frame. grow > 0 offsets the
    surface radially — used to carve the rib tips at RIB_CLR (Rev F)."""
    taper = Pos(0, 0, FLOOR_Z + CUP_TAPER_H / 2) * Cone(
        CUP_BASE_D / 2 + grow, CUP_TAPER_TOP_D / 2 + grow, CUP_TAPER_H
    )
    body_h = CUP_H - CUP_TAPER_H
    body = Pos(0, 0, FLOOR_Z + CUP_TAPER_H + body_h / 2) * Cone(
        CUP_TAPER_TOP_D / 2 + grow, CUP_RIM_D / 2 + grow, body_h
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


def run_checks(base_full, collar, clip, clips_placed, cups_placed, collars_placed):
    # Worst-case snap-in deflection is at the clip's OUTER corner, where the
    # stadium's end-circle pulls the plate edge inward (Rev B); worst lever is
    # the moment the plate edge rides over the tip (Rev D).
    deflect = HOOK_TIP_R - (PLATE_EDGE_MIN - INSERT_CLR)
    strain = 1.5 * CLIP_T * deflect / HOOK_TIP_Z**2
    bearing_z = HOOK_ROOT_Z - (PLATE_EDGE_MIN - TONGUE_FACE_R) * RAMP_SLOPE
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
    # kernel coverage: the fabric opening (its own stadium, conveniently on the
    # same 3.75 centers), grown by the required margin, must vanish under the
    # flange footprint — bbox comparison provably isn't enough here
    fabric_grown = stadium(FABRIC_W / 2 + 0.15)
    leftover = fabric_grown - stadium(FLANGE_R)
    uncovered_area = getattr(leftover, "area", 0.0) or 0.0
    flange_covers = uncovered_area < 1e-6
    # the -X extrude bug (Rev A dev) left the hook detached; prove the clip
    # part is one connected solid living entirely inside the head width
    t_bb = clip.bounding_box()
    clip_ok = (len(clip.solids()) == 1
               and max(abs(t_bb.min.X), abs(t_bb.max.X)) <= HEAD_W / 2 + 1e-3)
    # head bearing: strip of plug-wall top between the pocket's inner edge and
    # the leg slot that actually carries the pull-out load
    bearing_strip = (HEAD_DEPTH + POCKET_CLR) - (CLIP_T + CLIP_GAP)

    clr_bot = CONE_RI_B - cup_radius(SKIRT_Z0)
    clr_top = CONE_RI_T - cup_radius(COL_TOP)  # straight bore vs flaring cup (Rev F)

    # pre-twist position: lugs sit in the entry slots (kernel-proves alignment)
    pre_l = Pos(-BORE_CC / 2, 0, 0) * Rot(0, 0, TWIST) * collar.scale(1.0)

    checks = [
        ("plug fits recess/plate opening", PLUG_R <= HOLE_D / 2 - 0.02,
         f"plug r {PLUG_R:.3f} <= hole r {HOLE_D / 2:.3f} - 0.02"),
        ("nothing below the recess floor", TONGUE_BOT >= -(RECESS_DEPTH - 0.02),
         f"lowest point {TONGUE_BOT:.2f} >= {-(RECESS_DEPTH - 0.02):.2f}"),
        ("base folds into the seatback", base_top <= FOLD_LIMIT,
         f"base stands {base_top:.3f} above fabric <= {FOLD_LIMIT}"),
        ("flange covers the fabric opening EVERYWHERE (kernel)", flange_covers,
         f"(fabric stadium grown 0.15) - flange = {uncovered_area:.6f} in² "
         "(Rev A's bbox-only check missed the waist gap — Brian caught it)"),
        ("hook bears SNUG at the plate corner (Rev D)", abs(bearing_z + LEDGE) <= 0.015,
         f"ramp crosses the plate corner at {-bearing_z:.3f} below the flange seat "
         f"vs ledge {LEDGE:.3f} (Brian measured 11/16 slack-to-tip on Rev C's 45-deg ramp)"),
        ("hook bite is real but insertable", 0.06 <= HOOK_ENG <= POCKET_OUT - 0.02,
         f"bite {HOOK_ENG:.2f} past plate edge, pocket allows {POCKET_OUT - 0.02:.2f}"),
        ("hooks land in pockets under BOTH measured spacings", pocket_fit,
         f"hook span {hook_lo:.3f}..{hook_hi:.3f} in 1.0-wide pockets at c-c 3.5 AND 3.75"),
        ("hook clears pocket floor", TONGUE_BOT >= -(LEDGE + POCKET_BELOW_PLATE) + 0.05,
         f"tongue bottom {TONGUE_BOT:.2f} >= pocket floor {-(LEDGE + POCKET_BELOW_PLATE):.2f} + 0.05"),
        ("snap-in flex within PETG limit", strain <= PETG_STRAIN_LIMIT,
         f"strain {strain * 100:.2f}% <= {PETG_STRAIN_LIMIT * 100:.1f}% (deflect {deflect:.3f} over L {-HOOK_TIP_Z:.2f}, in-plane)"),
        ("collar supports the cup above its taper", COL_TOP >= FLOOR_Z + CUP_TAPER_H + 0.2,
         f"collar top {COL_TOP:.2f} >= taper top {FLOOR_Z + CUP_TAPER_H:.2f} + 0.2"),
        ("cup clearance to the collar WALL (bottom / top)",
         clr_bot >= 0.05 and clr_top >= 0.03,
         f"radial clr {clr_bot:.3f} / {clr_top:.3f} (>=0.05/0.03; Rev F ribs carry the "
         f"actual fit at {RIB_CLR:.3f})"),
        ("rib grip gap is snug but droppable", 0.008 <= RIB_CLR <= 0.03,
         f"RIB_CLR {RIB_CLR:.3f} — the Rev F anti-tip fit knob"),
        ("cups clear each other through the collar zone",
         # 0.15 relaxed to 0.10 at Rev F: the taller collar tops out where the
         # cups have converged to ~0.13 apart — seat geometry, consciously accepted
         BORE_CC - 2 * cup_radius(COL_TOP) >= 0.10,
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
        ("second collar drops in beside a LOCKED one (kernel, Rev E)",
         isect_vol(pre_l, collars_placed[1]) < 1e-4,
         "pre-twist left collar vs locked right collar — the U-notch carries the clearance"),
        ("cups touch neither collar nor base (kernel)",
         all(isect_vol(c, s) < 1e-4 for c in cups_placed
             for s in (collars_placed[0], collars_placed[1], base_full)),
         "reference cup solids vs everything"),
        ("clip part is one solid, inside the head width", clip_ok,
         f"{len(clip.solids())} solid(s), x span ±{max(abs(t_bb.min.X), abs(t_bb.max.X)):.3f}"),
        ("clip head has a real bearing strip on the wall top", bearing_strip >= 0.10,
         f"strip {bearing_strip:.3f} >= 0.10 (pull-out load seats the head, never lifts it)"),
        ("installed clips touch neither base nor collars (kernel)",
         all(isect_vol(c, s) < 1e-4 for c in clips_placed
             for s in (base_full, collars_placed[0], collars_placed[1])),
         "4 clips in pockets vs base and locked collars"),
        ("clip drops STRAIGHT DOWN into place (kernel, Rev G)",
         all(isect_vol(Pos(0, 0, dz) * clips_placed[0], base_full) < 1e-4
             for dz in (0.25, 0.55, 0.85)),
         "lifted clip clears the base along its whole insertion path — Rev F's "
         "pocket/slot overlap (0.134) jammed the 0.189 hook and snapped a clip"),
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
| {BASENAME}-base-{REV_TAG}.step | **1** | flange face DOWN | ~211 mm long — no supports; clip pockets bridge internally |
| {BASENAME}-collar-{REV_TAG}.step | **2** | wide (top) end DOWN | ring + lugs are 45°-chamfered (Rev C, per Casey) — no supports |
| {BASENAME}-clip-{REV_TAG}.step | **4 + spares** | LYING FLAT on its side | layer lines must run root→hook (Rev C: the upright-printed clip snapped at the root); ~10 min each |

Clip install: hold the clip vertical, hook outboard, and drop it STRAIGHT DOWN —
the hook passes through the open slot in the flange, then the T-head seats in its
pocket (light press; a drop of CA under the head is cheap insurance). Pull-out
loads seat the head deeper — the glue only guards against insertion wiggle. The
small open slot outboard of each head is the hook's way in (and a drain), not a
defect.

Every part ships as STEP (preferred: exact curves) AND STL (for mesh-only slicers
like Cura). Both are mm. Same geometry — use whichever your slicer imports.

## For the printer owner (thanks, neighbor)

Slice with your own known-good PETG profile — these settings are the only asks:

- **≥4 perimeters** — the 1.6 mm snap-clip tongues on the base must be solid wall, not infill.
- 30–40% infill, layer 0.2 mm or finer, PETG temps per your filament.
- **No supports** in the stated orientations (small overhangs on the collar lugs bridge fine).
- PETG on the CR-6 glass bed: use a glue-stick release layer — PETG can bond hard
  enough to chip the glass.
- Rough times at ordinary speeds: clip coupon ~15 min, collar coupon ~3 h,
  well coupon ~5 h, base ~6 h, each collar ~5 h.

Suggested batches: **(1)** clip coupon + collar coupon (~3.5 h) → Brian fit-tests in
the truck; **(2)** base + 2 collars (a weekend of unattended time). The well coupon is
an optional twist-lock test between the two if batch 1 raises doubts.

## Coupons — print and fit these BEFORE the full parts

| File | Tests |
|---|---|
| coupon/{BASENAME}-pocket-coupon-{REV_TAG}.step | the clip's mating SOCKET, cut from the real base (flange strip w/ head pocket + wall slot): press a printed clip in, then snap the pair into a truck pocket — engagement, removal force, flat-print layer survival. NOT a clip — the clip is the production part above. |
| coupon/{BASENAME}-well-coupon-{REV_TAG}.step | one full well ring (clip cutouts + bayonet slots) |
Collar fit test: print ONE full production collar — the old shortened collar
coupon let the cup wedge high in the loose cone and faked a snug fit (Rev F
lesson), so it is no longer generated. The bayonet twist test works with the
already-printed Rev A collar coupon (lugs/skirt unchanged since Rev A).

(Print at least one clip alongside the pocket coupon — the coupon is the POCKET;
the clip itself is the production part.)

If the clip coupon snaps (the part, not the click): thicken CLIP_T or shrink HOOK_ENG
in the script and regenerate — do not hand-tune prints.

## Assembly & use

1. Seat the four clips in their flange pockets (CA drop optional), then press the
   base into the platform recess until all four click under the plate.
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
    clip = clip_part()
    cup = build_cup()

    collar_l = Pos(-BORE_CC / 2, 0, 0) * collar.scale(1.0)
    collar_r = Pos(BORE_CC / 2, 0, 0) * Rot(0, 0, 180) * collar.scale(1.0)
    cup_l = Pos(-BORE_CC / 2, 0, 0) * cup.scale(1.0)
    cup_r = Pos(BORE_CC / 2, 0, 0) * cup.scale(1.0)
    clips_placed = place_clips(clip)

    checks = run_checks(base_full, collar, clip, clips_placed,
                        (cup_l, cup_r), (collar_l, collar_r))
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
    for i, gx in enumerate((-CLIP_CC / 2, CLIP_CC / 2)):
        for j, ang in enumerate((0, 180)):
            parts.append(place(Rot(0, 0, ang) * clip, f"clip{2 * i + j + 1}", x=gx))
    asm = Compound(children=parts)
    asm.label = f"{BASENAME}-{REV_TAG}"
    asm_path = OUT_DIR / f"{BASENAME}-assembly-{REV_TAG}.step"
    export_step(asm, str(asm_path))
    print(f"wrote {asm_path.name}")

    # print STEPs + STLs (one file per unique part; qty in the build sheet).
    # STLs are hand-off copies for mesh-only slicers (Cura) — gitignored,
    # never committed per repo policy.
    for shape, stem in ((base_full, "base"), (collar, "collar"), (clip, "clip")):
        located = place(shape, stem)
        p = OUT_DIR / f"{BASENAME}-{stem}-{REV_TAG}.step"
        export_step(located, str(p))
        export_stl(located, str(p.with_suffix(".stl")))
        print(f"wrote {p.name} (+.stl)")

    # coupons — cut straight out of the real geometry
    clip_zone = Pos(CLIP_CC / 2, 1.80, -0.3) * Box(1.05, 1.1, 1.6)
    well_zone = Pos(-BORE_CC / 2, 0, 0) * Cylinder(2.12, 4.0)
    # (the shortened collar coupon was retired at Rev F — it wedged the cup high
    # in the loose cone and reported a snug fit the real assembly didn't have;
    # the collar fit test is one full production collar)
    coupons = (
        (base_full & clip_zone, "pocket-coupon"),  # renamed from "clip-coupon"
        # (Brian read that as a coupon OF the clip; it's the clip's socket)
        (base_full & well_zone, "well-coupon"),
    )
    for shape, stem in coupons:
        located = place(shape, stem)
        p = COUPON_DIR / f"{BASENAME}-{stem}-{REV_TAG}.step"
        export_step(located, str(p))
        export_stl(located, str(p.with_suffix(".stl")))
        print(f"wrote coupon/{p.name} (+.stl)")

    sheet = write_buildsheet(OUT_DIR / f"{BASENAME}-buildsheet-{REV_TAG}.md")
    print(f"wrote {sheet.name}")


if __name__ == "__main__":
    main()
