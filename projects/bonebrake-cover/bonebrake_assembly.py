"""Bonebrake cover — 3-layer assembly per BRIEF.md.

Frame (welded flat-bar, screwed to brick) + middle panel + art face panel,
face+middle riveted on the bench (6x 3/16 SOLID rivets, bucked), unit held to
frame by 4x 1/4-20 flanged button bolts; shop heads nest in frame relief holes.

Outputs: STEP assembly (named components), face/middle plasma DXFs (from the
SAME sketches as the solids), frame cut list + drill schedule, check report.
This supersedes bonebrake_cover.py (the original 2D-only test path, kept for
reference).

Run:  ../../.venv/bin/python bonebrake_assembly.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from build123d import (  # noqa: E402
    Axis,
    Box,
    Circle,
    Face,
    Wire,
    Color,
    Compound,
    Cylinder,
    Pos,
    Rectangle,
    RectangleRounded,
    RegularPolygon,
    Rot,
    extrude,
    export_step,
    fillet,
    import_dxf,
    import_step,
)

from lib.drillmap import drill_map  # noqa: E402
from lib.materials import cost  # noqa: E402
from lib.fasteners import SCREWS, SOLID_RIVETS, screw_hole  # noqa: E402

# --------------------------------------------------------------- PARAMETERS
# All inches. REAL COVER (Michelle/Bonebrake). Test coupon was 2.5 x 6.25, bar 0.5.
# Site: jagged pipe channel in brick, ~12" widest, running floor to an OVERHANGING
# cap course at ~41.5" (her tape — VERIFY min under-cap height at L/C/R, and widest
# jag, before cutting). Install: slide up tight under the cap lip; carpet hides
# any shortfall at the floor. Side bars carry ALL brick bearing; top/bottom bars
# bridge the channel.
# Run `python bonebrake_assembly.py coupon` for the texture/test coupon
# (outputs land in output/coupon/); default run = the real cover.
COUPON = len(sys.argv) > 1 and sys.argv[1] == "coupon"

# Revision letter — stamped into every output filename and document header, and
# carried by hand into Fusion program names / posted gcode (e.g. face-revA.gcode).
# Bump on any form/fit/function change: dimensions, hole sizes, patterns, material,
# finish callouts, artwork. Letters per ASME Y14.35: skip I, O, Q, S, X, Z; after
# Y comes AA, AB, … The BRIEF's "Current revision" line and history table must be
# updated with every bump — a generation check enforces the match.
REV = "A"

if COUPON:
    W, H, BAR = 2.5, 6.25, 0.5
    OPENING_W, UNDER_CAP_H = 1.0, 999.0  # no site constraints on a coupon
else:
    OPENING_W = 5.5    # Brian's estimate + hedge (Michelle's 12 was generous) — VERIFY w/ tape
    UNDER_CAP_H = 41.5 # her measurement — VERIFY (use MINIMUM of L/C/R)
    W = 9.0
    H = 41.25          # UNDER_CAP_H - 0.25 slide-in clearance; deficit hides in carpet
    BAR = 1.5          # flat-bar width
FRAME_T = 0.25         # flat-bar thickness
PANEL_T = 0.125        # 11ga modeled at nominal 1/8 (actual 0.1196 runs safe-shy)
PANEL_MATERIAL = "11ga mild steel"   # shown in the program table Jimmie cuts from
# Coupon cuts 2 middles: one per candidate gray texture (engine-turned vs
# stone-texture can) for Michelle's finish choice. Real cover needs only 1.
PANEL_QTY = {"face": 1, "middle": 2 if COUPON else 1}
CORNER_R = 0.125       # face/middle corner radius

BOLT = "1/4-20"        # corner bolts: black-oxide flanged button head hex, 1/4-20 x 1/2
# Coarse thread (1/4-28 fine variant considered, coarse chosen: standard tap + cheaper).

BOLT_FLANGE_DIA = 0.58   # approximate — catalog STEP supersedes primitive dims
BOLT_DOME_DIA = 0.44
BOLT_HEAD_H = 0.165
BOLT_LEN = 0.5           # 1/2" = flush with frame back at nominal stack (0.500)

# Catalog hardware (McMaster STEP downloads) — used when the file exists in
# lib/hardware/, else the parametric primitive below stands in. Convention for
# both: origin at the head's bearing plane, shank pointing -Z. Tune each
# model's rotate/z_shift once after downloading (catalog orientations vary).
# Filename convention: <type>-<head/drive>-<thread>x<length>-<finish>-<sku>.step
# Config matches on the spec prefix (glob) so finish/SKU need no code change.
BOLT_MODEL = {"file": "bolt-flangedbutton-hex-1_4-20x1_2-*.step", "rotate_x": 0.0, "z_shift": 0.0}
RIVET_MODEL = {"file": "rivet-solid-brazier-3_16x1_2-*.step", "rotate_x": 0.0, "z_shift": 0.0}

# SOLID rivets (bucked on the bench — unit has back-side access; POP rejected).
RIVET_SIZE = "3/16"
SOLID = SOLID_RIVETS[RIVET_SIZE]
RIVET_LEN = 0.5        # stack + ~1.5d tail for the shop head; the 3/8" ones on
                       # hand are too short (0.67d tail) — the check below fails them
SHOP_HEAD_DIA = 1.5 * SOLID["shank_dia"]   # formed shop head ~1.5d x 0.5d
SHOP_HEAD_H = 0.5 * SOLID["shank_dia"]
RELIEF_DIA = 11 / 32   # frame holes hosting the shop heads (dia + placement margin)

# As-built hole sizes chosen from a FRACTIONAL drill index (Jimmie's bench).
# Per-role rounding: clearance rounds UP, rivet fit stays snug, tap drill uses
# the published fractional equivalent of #7. B and C share one 13/64 bit.
BOLT_CLEAR_DIA = 9 / 32    # 0.281 — bolt clearance (up from close-fit F 0.257)
RIVET_HOLE_DIA = 13 / 64   # 0.203 — solid-rivet snug fit (shank swells to fill)
TAP_DRILL_DIA = 13 / 64    # 0.203 — 1/4-20 tap drill, ~72% thread


def frac(d: float) -> str:
    from fractions import Fraction
    f = Fraction(d).limit_denominator(64)
    return f"{f.numerator}/{f.denominator}"

OUT_DIR = Path(__file__).parent / "output" / ("coupon" if COUPON else "")
BASENAME = "bonebrake-coupon" if COUPON else "bonebrake"
REV_TAG = f"rev{REV}"          # filename form; documents print "Rev A"
OUT_STEP = OUT_DIR / f"{BASENAME}-assembly-{REV_TAG}.step"
DRILLMAP_NAME = f"{BASENAME}-drillmap-{REV_TAG}.svg"
BOM_NAME = f"{BASENAME}-bom-{REV_TAG}.md"
BUILDSHEET_NAME = f"{BASENAME}-buildsheet-{REV_TAG}.md"
CAMSHEET_NAME = f"{BASENAME}-camsheet-{REV_TAG}.md"
BRIEF_PATH = Path(__file__).parent / "BRIEF.md"


def dxf_name(panel: str) -> str:
    return f"{BASENAME}-{panel}-{REV_TAG}.dxf"

# Plasma can't cut clean holes near material thickness — panel DXFs carry small
# PILOT circles at every hole position (plasma cuts them rough, Jimmie drills to
# final size per the panel drill schedule). The 3D solids show finished holes.
# Pilots cut with the small-hole CAM recipe (DECIDED 2026-08-25): a separate
# holes-only 2D Profile op with Sideways Compensation = CENTER, Pierce
# Clearance = 0, Lead-In/Out OFF. Under that recipe the floor is ~2x kerf.
# The full recipe is emitted as a generated CAM sheet (write_camsheet).
# Normal-comp inside profiles need >= PLASMA_MIN_HOLE (~3/16 on the ArcDroid).
PLASMA_KERF = 0.055
PLASMA_MIN_HOLE = 0.1875   # normal-comp ops only; pilots use the center-comp recipe
PILOT_DIA = 0.125

# Artwork cut into the face layer. Coupon uses the original tree; the real
# cover uses artwork-final.dxf once Brian drops it in artwork/ (tree stands in
# as a loud placeholder until then).
ART_DIR = Path(__file__).parent / "artwork"
# Coupon: the original tree. Real cover: artwork-final.svg OR .dxf (either works —
# auto-fit needs only the aspect ratio, so SVG unit ambiguity is harmless).
# Export requirements for final art: art paths only (no border/frame), text outlined.
ART_MARGIN = 0.25   # side keep-out
ART_BAND = 0.75     # top/bottom keep-out (matches the approved 2D fit)

# --------------------------------------------------------------- PATTERNS

CORNER_INSET = BAR / 2


def corner_pattern() -> list[tuple[float, float]]:
    x, y = W / 2 - CORNER_INSET, H / 2 - CORNER_INSET
    return [(-x, y), (x, y), (-x, -y), (x, -y)]


RIVET_SPACING_TARGET = 8.0  # rows derived from height unless overridden
# Coupon: 4 rivets total. Real: height-derived = 5 pairs (10), matching the
# concept render — DECIDED 2026-08-25. Possible Michelle choice later: set
# `3` here for the 6-rivet variant, render both, let her pick.
RIVET_ROWS = 2 if COUPON else None


def rivet_pattern() -> list[tuple[float, float]]:
    """Evenly spaced pairs down the sides between the corner bolts, rows by height."""
    x = W / 2 - BAR / 2
    y_top = H / 2 - CORNER_INSET
    span = 2 * y_top
    rows = RIVET_ROWS if RIVET_ROWS else max(3, round(span / RIVET_SPACING_TARGET))
    step = span / (rows + 1)
    ys = [-y_top + step * (i + 1) for i in range(rows)]
    return [(sx, y) for y in ys for sx in (-x, x)]


# --------------------------------------------------------------- GEOMETRY


def punched(sketch, holes: list[tuple[tuple[float, float], float]]):
    for (px, py), dia in holes:
        sketch -= Pos(px, py) * Circle(dia / 2)
    return sketch


def build_frame():
    # Outer corners rounded to match the panels (ground after welding);
    # window corners stay square — that's what the miter joint produces.
    sk = RectangleRounded(W, H, CORNER_R) - Rectangle(W - 2 * BAR, H - 2 * BAR)
    sk = punched(
        sk,
        [(p, TAP_DRILL_DIA) for p in corner_pattern()]
        + [(p, RELIEF_DIA) for p in rivet_pattern()],
    )
    solid = extrude(sk, FRAME_T)
    solid.label = "frame"
    return solid


IN = 25.4  # STEP is mm; parts are scaled at origin then placed in mm.


# STEP carries flat RGB colors (not Fusion Appearances) — bake them here so
# every re-import arrives pre-tinted and appearance work isn't redone.
COLORS = {
    "frame": Color(0.10, 0.10, 0.10),   # black
    "middle": Color(0.62, 0.62, 0.62),  # light/medium gray contrast behind art
    "face": Color(0.10, 0.10, 0.10),    # black
    "screw": Color(0.13, 0.13, 0.13),   # black oxide
    "rivet": Color(0.80, 0.80, 0.82),   # aluminum
}


def place(part, x: float, y: float, z: float, label: str, scale: bool = True):
    """Place a part at inch coords (x, y, z). scale=True for origin-built inch
    primitives (converted to mm first); False for imported catalog models,
    which arrive from STEP already in mm."""
    # scale() also serves as a copy: each placement needs its own shape object,
    # or every instance shares one label/color slot (catalog import bug, caught
    # 2026-08-24 — four screws all exported as "screw4").
    shaped = part.scale(IN if scale else 1.0)
    located = Pos(x * IN, y * IN, z * IN) * shaped
    located.label = label
    color = COLORS.get(label.rstrip("0123456789"))
    if color is not None:
        located.color = color
    return located


HARDWARE_DIR = REPO_ROOT / "lib" / "hardware"


def normalize_fastener(shape):
    """Auto-orient a catalog fastener to our convention: bearing plane at the
    origin, head +Z, shank -Z.

    Heuristic: a fastener's largest flat face perpendicular to its axis is the
    head's bearing surface. The head lies on the side of that face nearer an
    end (head height << shank length) — flip if it points down, then shift the
    bearing face to z=0. Vendors model origins wherever they like (McMaster:
    part center), so never trust the file's origin.
    """
    flat = [f for f in shape.faces() if abs(abs(f.normal_at().Z) - 1) < 1e-3]
    bearing = max(flat, key=lambda f: f.area)
    bz = bearing.center().Z
    bb = shape.bounding_box()
    head_up = (bb.max.Z - bz) <= (bz - bb.min.Z)
    if not head_up:
        shape = Rot(180, 0, 0) * shape
        bz = -bz
    return Pos(0, 0, -bz) * shape


def catalog_or(primitive_fn, model: dict):
    """Imported catalog STEP if downloaded, else the parametric primitive.

    Returns (shape, is_catalog). Catalog shapes are auto-normalized (see
    normalize_fastener); the config's rotate_x/z_shift apply on top for
    models the heuristic can't handle.
    """
    matches = sorted(HARDWARE_DIR.glob(model["file"]))
    if not matches:
        return primitive_fn(), False
    if len(matches) > 1:
        print(f"  note: {model['file']} matched {len(matches)} files, using {matches[0].name}")
    shape = normalize_fastener(import_step(str(matches[0])))
    if model["rotate_x"]:
        shape = Rot(model["rotate_x"], 0, 0) * shape
    if model["z_shift"]:
        shape = Pos(0, 0, model["z_shift"] * IN) * shape
    print(f"  catalog: {matches[0].name}")
    return shape, True


def load_art_faces(art_file: Path) -> list:
    """Closed faces from an art file — SVG (filled paths) or DXF (stitched curves)."""
    if art_file.suffix.lower() == ".svg":
        from build123d import import_svg
        shapes = import_svg(str(art_file), flip_y=True)
        faces = [sh for sh in shapes if isinstance(sh, Face)]
        faces += [Face(w) for w in shapes if isinstance(w, Wire) and w.is_closed]
        return faces
    edges = list(import_dxf(str(art_file)))
    splines = [c for c in edges if type(c).__name__ == "BSpline"]
    wires = Wire.combine(splines if splines else edges)
    return [Face(w) for w in wires if w.is_closed]


def artwork_face():
    """The art as a single Face, scaled and centered onto the panel — or None."""
    if COUPON:
        art_file = ART_DIR / "ArtLayer.dxf"
        if not art_file.exists():
            return None
    else:
        finals = sorted(
            f for f in ART_DIR.iterdir()
            if "final" in f.stem.lower() and f.suffix.lower() in (".dxf", ".svg")
        )
        if finals:
            art_file = finals[0]
        elif (ART_DIR / "ArtLayer.dxf").exists():
            print("  !! artwork-final.(svg|dxf) not found — using coupon tree as PLACEHOLDER")
            art_file = ART_DIR / "ArtLayer.dxf"
        else:
            return None
    faces = load_art_faces(art_file)
    if not faces:
        return None
    print(f"  artwork: {art_file.name} -> {len(faces)} face(s)")
    raw = faces[0] if len(faces) == 1 else Compound(children=faces)
    bb = raw.bounding_box()
    s = min((W - 2 * ART_MARGIN) / bb.size.X, (H - 2 * ART_BAND) / bb.size.Y)
    # Fit as large as possible, then back off until the kernel proves the art
    # clears every fastener keep-out zone (first run grazed a rivet by 0.0002).
    for _ in range(10):
        art = raw.scale(s)
        c = art.bounding_box().center()
        art = Pos(-c.X, -c.Y) * art
        if art_hole_overlap(art) < 1e-6:
            print(f"  artwork: fit at scale {s:.4f}")
            return art
        s *= 0.98
    raise RuntimeError("artwork cannot clear fastener holes even at 82% of max fit")


def panel_sketch(art=None, pilots=False):
    """The panel profile — single source for both the solid and the plasma DXF.

    pilots=True (DXF/CAM): every hole is a PILOT_DIA circle for plasma pierce,
    drilled to final size afterward. pilots=False (solids): finished holes.
    """
    sk = RectangleRounded(W, H, CORNER_R)
    if pilots:
        holes = [(p, PILOT_DIA) for p in corner_pattern() + rivet_pattern()]
    else:
        holes = [(p, BOLT_CLEAR_DIA) for p in corner_pattern()] + [
            (p, RIVET_HOLE_DIA) for p in rivet_pattern()
        ]
    sk = punched(sk, holes)
    if art is not None:
        sk = sk - art
    return sk


def build_panel(name: str, art=None):
    """Panel at origin, z [0, PANEL_T] — placed (and scaled) later via place()."""
    return extrude(panel_sketch(art), PANEL_T)


def flanged_button_bolt_primitive():
    """Flanged button-head hex bolt: bearing plane at origin, shank -Z.

    Dims approximate — the downloaded catalog STEP supersedes this primitive.
    """
    flange_h = 0.03
    shank = Pos(0, 0, -BOLT_LEN / 2) * Cylinder(SCREWS[BOLT]["major_dia"] / 2, BOLT_LEN)
    flange = Pos(0, 0, flange_h / 2) * Cylinder(BOLT_FLANGE_DIA / 2, flange_h)
    dome_h = BOLT_HEAD_H - flange_h
    dome = Pos(0, 0, flange_h + dome_h / 2) * Cylinder(BOLT_DOME_DIA / 2, dome_h)
    bolt = shank + flange + dome
    bolt = fillet(bolt.edges().group_by(Axis.Z)[-1], dome_h * 0.6)
    # hex-drive recess: cosmetic hexagonal pocket (5/32 across flats)
    hex_af = 0.156
    hex_r = hex_af / 1.7320508  # across-flats -> circumradius
    hex_pocket = Pos(0, 0, BOLT_HEAD_H - 0.04) * extrude(RegularPolygon(hex_r, 6), 0.08)
    return bolt - hex_pocket


def rivet_primitive():
    """Bucked solid rivet, as-installed: brazier factory head at origin,
    swelled shank through the stack, formed shop head below."""
    d = SOLID["shank_dia"]
    stack = 2 * PANEL_T
    shank = Pos(0, 0, -stack / 2) * Cylinder(d / 2, stack)
    shop = Pos(0, 0, -stack - SHOP_HEAD_H / 2) * Cylinder(SHOP_HEAD_DIA / 2, SHOP_HEAD_H)
    head = Pos(0, 0, SOLID["head_height"] / 2) * Cylinder(SOLID["head_dia"] / 2, SOLID["head_height"])
    rivet = shank + shop + head
    return fillet(rivet.edges().group_by(Axis.Z)[-1], SOLID["head_height"] * 0.45)


def build_fasteners(stack_top: float):
    """Fastener solids at every pattern position — catalog models when present."""
    parts = []
    bolt, bolt_is_catalog = catalog_or(flanged_button_bolt_primitive, BOLT_MODEL)
    for i, (px, py) in enumerate(corner_pattern(), 1):
        parts.append(place(bolt, px, py, stack_top, f"screw{i}", scale=not bolt_is_catalog))
    rivet, rivet_is_catalog = catalog_or(rivet_primitive, RIVET_MODEL)
    for i, (px, py) in enumerate(rivet_pattern(), 1):
        parts.append(place(rivet, px, py, stack_top, f"rivet{i}", scale=not rivet_is_catalog))
    return parts


# --------------------------------------------------------------- CHECKS


def art_hole_overlap(art) -> float:
    """Total area where the art face invades any fastener hole (+ margin)."""
    if art is None:
        return 0.0
    holes = [(p, BOLT_CLEAR_DIA) for p in corner_pattern()] + [
        (p, RIVET_HOLE_DIA) for p in rivet_pattern()
    ]
    bad = 0.0
    for (px, py), dia in holes:
        zone = Pos(px, py) * Circle(dia / 2 + 0.05)
        common = art & zone
        bad += getattr(common, "area", 0.0)
    return bad


def run_checks(art=None) -> list[tuple[str, bool, str]]:
    clamped = 2 * PANEL_T
    d = SOLID["shank_dia"]
    tail_ratio = (RIVET_LEN - clamped) / d
    bar_x_min = W / 2 - BAR  # inner edge of side bar
    checks = [
        ("window exists (W)", W - 2 * BAR > 0, f"window W = {W - 2 * BAR:.3f}"),
        (
            "side bars bear fully on brick past the jag",
            W / 2 - BAR >= OPENING_W / 2 + 0.25,
            f"bar inner edge {W / 2 - BAR:.2f} >= jag {OPENING_W / 2:.2f} + 0.25",
        ),
        (
            "cover fits under the cap lip w/ slide-in room",
            H + 0.25 <= UNDER_CAP_H,
            f"H {H:.2f} + 0.25 <= under-cap {UNDER_CAP_H:.2f}",
        ),
        ("window exists (H)", H - 2 * BAR > 0, f"window H = {H - 2 * BAR:.3f}"),
        (
            "rivet tail forms a proper shop head (1.3-1.7d)",
            1.3 <= tail_ratio <= 1.7,
            f"tail {RIVET_LEN - clamped:.3f} = {tail_ratio:.2f}d (target 1.5d)",
        ),
        (
            "shop head hides inside frame",
            SHOP_HEAD_H <= FRAME_T,
            f"shop head h {SHOP_HEAD_H:.3f} <= bar {FRAME_T:.3f}",
        ),
        (
            "shop head clears relief hole",
            SHOP_HEAD_DIA < RELIEF_DIA,
            f"shop head {SHOP_HEAD_DIA:.3f} < relief {RELIEF_DIA:.3f}",
        ),
        (
            "rivet holes land on side bar",
            all(abs(px) - RELIEF_DIA / 2 > bar_x_min for px, _ in rivet_pattern()),
            f"rivet x ±{W / 2 - BAR / 2:.3f}, bar inner edge ±{bar_x_min:.3f}",
        ),
        (
            "screw does not protrude into brick",
            BOLT_LEN <= FRAME_T + 2 * PANEL_T,
            f"shank {BOLT_LEN:.3f} <= stack {FRAME_T + 2 * PANEL_T:.3f}",
        ),
        (
            "thread engagement >= 2 full threads",
            (BOLT_LEN - 2 * PANEL_T) * SCREWS[BOLT]["tpi"] >= 2,
            f"{(BOLT_LEN - 2 * PANEL_T) * SCREWS[BOLT]['tpi']:.1f} threads engaged in frame",
        ),
        (
            "corner holes land on bar",
            CORNER_INSET + TAP_DRILL_DIA / 2 <= BAR,
            f"inset {CORNER_INSET:.3f} + tap r <= bar {BAR:.3f}",
        ),
        (
            "rivet hole is a snug solid-rivet fit",
            0 < RIVET_HOLE_DIA - SOLID["shank_dia"] <= 0.02,
            f"hole {frac(RIVET_HOLE_DIA)} - shank {SOLID['shank_dia']:.4f} = {RIVET_HOLE_DIA - SOLID['shank_dia']:.4f}",
        ),
        (
            "bolt clearance actually clears",
            BOLT_CLEAR_DIA > SCREWS[BOLT]["major_dia"],
            f"hole {frac(BOLT_CLEAR_DIA)} > major {SCREWS[BOLT]['major_dia']:.3f}",
        ),
        (
            "pilot cuttable under center-comp recipe (>= 2x kerf)",
            PILOT_DIA >= 2 * PLASMA_KERF,
            f"pilot {frac(PILOT_DIA)} >= 2 x kerf {PLASMA_KERF:.3f} (center-comp, pierce clearance 0)",
        ),
        (
            "pilot under every finish drill (light cleanup accepted)",
            PILOT_DIA <= min(RIVET_HOLE_DIA, TAP_DRILL_DIA, BOLT_CLEAR_DIA) - 0.01,
            f"pilot {frac(PILOT_DIA)} <= smallest finish {frac(min(RIVET_HOLE_DIA, TAP_DRILL_DIA, BOLT_CLEAR_DIA))} - 0.01",
        ),
        (
            "artwork clears every fastener hole",
            art_hole_overlap(art) < 1e-6,
            f"overlap area {art_hole_overlap(art):.6f} (kernel-verified boolean)",
        ),
        (
            "BRIEF current revision matches script REV",
            f"Current revision: **{REV}**" in BRIEF_PATH.read_text(),
            f'BRIEF.md contains "Current revision: **{REV}**" (on bump: update line + history table)',
        ),
    ]
    return checks


# --------------------------------------------------------------- CUT LIST


def print_cut_list() -> None:
    tap = TAP_DRILL_DIA
    relief = RELIEF_DIA
    print(f"\nFRAME CUT LIST (Rev {REV}) — 0.25 x", BAR, "flat bar, 45-deg miters both ends")
    print(f"  2 pcs  long-point {H:.3f}  (sides)")
    print(f"  2 pcs  long-point {W:.3f}  (top/bottom)")
    print("DRILL SCHEDULE (frame, after welding):")
    for px, py in corner_pattern():
        print(f'  ({px:+.3f}, {py:+.3f})  drill {frac(tap)}" -> tap {BOLT}')
    for px, py in rivet_pattern():
        print(f'  ({px:+.3f}, {py:+.3f})  drill {frac(relief)}"  (shop-head relief)')
    print("  brick-mount holes: 4x 1/4-20 flat head — drill + countersink ON-SITE")
    print(f"PANEL DRILL SCHEDULE (face + middle, from {frac(PILOT_DIA)} plasma pilots):")
    for px, py in corner_pattern():
        print(f'  ({px:+.3f}, {py:+.3f})  drill {frac(BOLT_CLEAR_DIA)}"  (bolt clearance, both panels)')
    for px, py in rivet_pattern():
        print(f'  ({px:+.3f}, {py:+.3f})  drill {frac(RIVET_HOLE_DIA)}"  (rivet, both panels)')
    print("  tip: clamp face+middle and drill the pairs together — guarantees alignment")


# --------------------------------------------------------------- BOM


def catalog_sku(model: dict) -> str:
    """SKU parsed from the matched hardware filename (…-<sku>.step), or TBD."""
    matches = sorted(HARDWARE_DIR.glob(model["file"]))
    return matches[0].stem.split("-")[-1] if matches else "TBD"


def write_bom(out_path: Path) -> Path:
    bar_run = 2 * (W + H)                # sum of long-point lengths
    bar_buy = bar_run + 4 * 0.25         # + saw kerf/handling allowance
    bar_ft = bar_buy / 12
    sheet_sqft = 2 * W * H / 144
    bar_cost = cost("flat_bar_1_4x1_5", bar_ft)
    sheet_cost = cost("sheet_11ga", sheet_sqft)
    sheet_note = (f"2 pcs {W:.2f} x {H:.2f} = {sheet_sqft:.1f} sqft "
                  f"(~${sheet_cost:.0f}; nest together; art cut in face only)")
    rows = [
        ("Flat bar 1/4 x " + f'{BAR:.2g}"' + " mild steel", "frame",
         f'{bar_run:.1f}" net — buy ≥ {bar_buy:.0f}" ({bar_ft:.1f} ft, ~${bar_cost:.0f})',
         "steel supplier"),
        ("Sheet 11ga mild steel", "face + middle panels", sheet_note, "steel supplier"),
        (f"Bolt, {BOLT} x 1/2 flanged button head hex, black-oxide", "unit → frame",
         "4 (pack of 25 on order)", f"McMaster {catalog_sku(BOLT_MODEL)}"),
        (f'Solid rivet, {RIVET_SIZE} x {RIVET_LEN:.2g}" brazier head, aluminum',
         "face+middle (bucked)", f"{len(rivet_pattern())} + spares",
         f"McMaster {catalog_sku(RIVET_MODEL)} / Amazon on hand"),
        ('Tapcon 1/4" x 1-1/4" flat Phillips head (masonry screw)', "frame → brick (on-site)",
         "4 (box incl. 3/16 carbide pilot bit)", "hardware store"),
        ("Spray: hammered black (face + frame); satin light gray (middle)", "finish",
         "1 can each", "hardware store"),
    ]
    lines = [
        f"# Bonebrake Cover — BOM  (Rev {REV}, {W:.2f} x {H:.2f})",
        "",
        f"Generated by bonebrake_assembly.py at Rev {REV} — regenerate, don't hand-edit.",
        "",
        "| Item | Used for | Qty / stock | Source |",
        "|---|---|---|---|",
    ]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", f"Material cost (price book): bar ~${bar_cost:.2f} + sheet ~${sheet_cost:.2f} "
              f"= **~${bar_cost + sheet_cost:.0f}** (hardware/paint extra; prices in lib/materials.py)"]
    lines += ["", f"Drill index needed: {frac(RIVET_HOLE_DIA)} (B+C), {frac(BOLT_CLEAR_DIA)} (A), "
              f"{frac(RELIEF_DIA)} (D), 1/4-20 tap; on-site: 3/16 carbide (SDS), 9/32 + 82-deg countersink for Tapcon heads."]
    out_path.write_text("\n".join(lines) + "\n")
    return out_path


# --------------------------------------------------------------- BUILD SHEET


def write_buildsheet(out_path: Path) -> Path:
    bolt_sku = catalog_sku(BOLT_MODEL)
    rivet_sku = catalog_sku(RIVET_MODEL)
    n_riv = len(rivet_pattern())
    middles = PANEL_QTY["middle"]
    clamp_stack = ("face on middle" if middles == 1
                   else f"face on BOTH middles ({middles + 1}-sheet stack)")
    extra_middle_note = "" if middles == 1 else (
        "\n- BOTH middles get the full drill pattern — either can then be bolted into"
        "\n  the stack for texture photos; rivet only after the finish choice."
    )
    text = f"""# Bonebrake Cover — Build Sheet  (Rev {REV}, {W:.2f} x {H:.2f})

Generated by bonebrake_assembly.py at Rev {REV} — regenerate, don't hand-edit.
Companion docs: {DRILLMAP_NAME} (hole letters referenced below), {BOM_NAME}.

**Revision rule:** every file for this job carries `{REV_TAG}` in its filename — DXFs, this
sheet, and the gcode posted from Fusion (name programs `…-{REV_TAG}.gcode`). Before cutting,
check the filename on the ArcDroid screen ends in `{REV_TAG}`; if it doesn't, or two revs of
any file are visible, STOP — stale file. Current-rev files live on the PPBO Job; superseded
attachments are removed there when a new rev is released.

## 1. Frame weldment (fab print)

Material: 1/4 x {BAR:.2g}" flat bar, mild steel. Cut per cut list — 45-deg miters both ends:
- 2 pcs long-point {H:.3f}" (sides)
- 2 pcs long-point {W:.3f}" (top/bottom)

Requirements (the what — technique is yours):
- Finished frame {W:.3f} x {H:.3f} outside, square within 1/32 across diagonals, FLAT
  (back face seats against brick; panels seat against front face).
- Weld outside corners, grind flush; round outer corners to ~{CORNER_R:.3g}" radius to
  match the panels.
- Window stays open — no welds inside.
- Drill AFTER welding, per drill map: 4x C ({frac(TAP_DRILL_DIA)}") at corners -> tap {BOLT};
  {n_riv}x D ({frac(RELIEF_DIA)}") rivet reliefs. Positions on the drill map / drill schedule.
- Brick-mount holes are NOT drilled in the shop — drilled + countersunk on-site at install.

## 2. Panels (from plasma blanks)

Plasma programs — what to cut, how many, and the blank each needs:

{program_table()}

Face (art cut in) + middle (plain), plasma-cut with {frac(PILOT_DIA)}" pilot holes.
- Clamp {clamp_stack}, art side up, edges flush. Drill pilot pairs TOGETHER:
  4x A ({frac(BOLT_CLEAR_DIA)}"), {n_riv}x B ({frac(RIVET_HOLE_DIA)}"). Deburr.{extra_middle_note}
- CAM: full Fusion op settings (small-hole pilot recipe + profile ops) are in
  {CAMSHEET_NAME} — set up from that sheet, not from memory.

## 3. Bench assembly (riveted unit)

- Orientation: face art side OUT, middle gray side toward the art cutout.
- {len(rivet_pattern())}x solid rivet {RIVET_SIZE} x {RIVET_LEN:.2g}" brazier ({rivet_sku}): insert from the FACE side
  (factory heads show on the face), buck shop heads on the middle's back.
  Shop heads must stand proud no more than ~{SHOP_HEAD_H:.2f}" (they nest in the frame reliefs).

## 4. Finish (before bench assembly)

- Face + frame: **hammered black** rattle-can (Rust-Oleum Hammered or equiv).
- Middle: field = light gray, **textured — technique TBD** (leading options:
  engine-turned swirls + clear coat, or gray stone-texture rattle can; texture
  scale must stay fine — it shows only through cutout slivers).
  **Middle EDGES painted black** (all 4 sides) — no gray stripe on the assembly edge.
- Prep beats paint: degrease, scuff/flap-disc the mill scale off show faces,
  clean out plasma dross from the art edges — hammered hides grind marks, not grease.
- Paint AFTER all drilling/tapping, BEFORE riveting (rivets stay bright aluminum).
- MASK the 4 tapped corner holes in the frame (paint in threads binds bolts —
  or chase threads after). Countersinks get drilled at install, so no masking needed there.
- Expect minor touch-up at rivet holes after bucking.

## 5. Fit-up + install

- Shop fit check: set riveted unit on frame — shop heads drop into the D reliefs,
  unit sits FLAT on the frame. Run all 4 bolts ({BOLT} x 1/2 flanged button, {bolt_sku})
  through A holes into the tapped corners. Snug only — 11ga under a flange, not a
  head gasket.
- Site: hold frame level, mark 4 Tapcon positions through the bar (installer's
  choice — clear of the C/D holes, 1"+ from brick edges; brick body or mortar
  joint, your call at this load). Drill frame 9/32 + countersink 82-deg for the
  flat heads. SDS-drill brick 3/16 carbide, 1-1/2" deep; blow out dust. Drive
  4x Tapcon 1/4 x 1-1/4 flat Phillips — heads FLUSH (panels seat against this
  face). Frame is permanent; all future service is the 4 corner bolts.
  Then hang the unit and run the corner bolts.
"""
    out_path.write_text(text)
    return out_path


# --------------------------------------------------------------- CAM SHEET


def program_table() -> str:
    """Markdown table of plasma programs: name, material, qty, blank size.
    Embedded in BOTH the CAM sheet and the build sheet — this is the one place
    that states how many of each part to cut. Blank W/H = part bounding box
    rounded UP to the next 1/2\" (never down — a plan smaller than the part
    is a trap)."""
    from math import ceil

    def half_up(v: float) -> float:
        return ceil(v * 2) / 2

    bw, bh = half_up(W), half_up(H)
    lines = [
        "| Program | Material | Qty | Blank W | Blank H |",
        "|---|---|---|---|---|",
    ]
    for panel in ("face", "middle"):
        lines.append(
            f'| {BASENAME}-{panel}-{REV_TAG}.gcode | {PANEL_MATERIAL} '
            f'| **{PANEL_QTY[panel]}** | {bw:g}" | {bh:g}" |'
        )
    lines.append(
        f'\nCut EXACTLY the quantities above — nothing else on the drive is current. '
        f'Blank sizes are the part bbox ({W:.2f} x {H:.2f} exact) rounded up to the '
        f'next 1/2"; leave your usual edge/start clearance beyond that.'
    )
    return "\n".join(lines)


def write_camsheet(out_path: Path, has_art: bool) -> Path:
    """Fusion CAM setup checklist for the plasma DXFs — the small-hole recipe
    settings live HERE (single source), not in anyone's memory."""
    n_pilots = len(corner_pattern()) + len(rivet_pattern())
    face_dxf, middle_dxf = dxf_name("face"), dxf_name("middle")
    art_line = (
        "art cutouts + outer profile — cut art (inside profiles) BEFORE the outline"
        if has_art else "outer profile only (no art on this config's face)"
    )
    text = f"""# Bonebrake Cover — CAM Sheet  (Rev {REV}, {W:.2f} x {H:.2f})

Generated by bonebrake_assembly.py at Rev {REV} — regenerate, don't hand-edit.
Import each DXF: Insert DXF, **Units = Inch** (dialog ignores the file's declared units).
Post programs named to match the rev — `{BASENAME}-face-{REV_TAG}.gcode`, `{BASENAME}-middle-{REV_TAG}.gcode` (Fusion suggests "1001"; overwrite it — .gcode is our extension, it's what Jimmie expects) — and attach to the PPBO Job, removing superseded revs.

## Programs to cut

{program_table()}

Two ops per panel; the ONLY difference between panels is the face's artwork.

## Op 1 — pilot holes only (small-hole recipe, both panels)

Select: the {n_pilots}x {frac(PILOT_DIA)}" pilot circles and NOTHING else.

| Setting (tab → group) | Value |
|---|---|
| Passes → Sideways Compensation | **Center** |
| Linking → Leads → Lead-In (Entry) | **unchecked** |
| Linking → Leads → Lead-Out (Exit) | **unchecked** |
| Linking → Piercing → Pierce Clearance | **0.00 in** |

Why: normal comp refuses profiles under ~{frac(PLASMA_MIN_HOLE)}" and the default pierce clearance can't fit inside the pilot. Center comp cuts ON the line — the hole opens to ~pilot + kerf ({PILOT_DIA + PLASMA_KERF:.3f}"), rough is fine: every pilot gets drilled to final size per the drill schedule.

## Op 2 — profiles (normal op, per panel)

| DXF | Select |
|---|---|
| {face_dxf} | {art_line} |
| {middle_dxf} | outer profile only |

Settings: normal Sideways Compensation (kerf {PLASMA_KERF:.3f}" stays in CAM), standard leads/pierce. Do NOT include the pilot circles in this op — they're Op 1's.
"""
    out_path.write_text(text)
    return out_path


# --------------------------------------------------------------- MAIN


def main() -> None:
    print(f"Bonebrake {'coupon' if COUPON else 'cover'} — Rev {REV}")
    art = artwork_face()
    if art is None:
        print("note: no artwork file — face generates uncut")
    checks = run_checks(art)
    print("VALIDATION:")
    ok = True
    for name, passed, detail in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        ok = ok and passed
    if not ok:
        print("\nFAILED checks — no geometry written.")
        sys.exit(1)

    frame = place(build_frame(), 0, 0, 0, "frame")
    middle = place(build_panel("middle"), 0, 0, FRAME_T, "middle")
    face = place(build_panel("face", art=art), 0, 0, FRAME_T + PANEL_T, "face")
    fasteners = build_fasteners(stack_top=FRAME_T + 2 * PANEL_T)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Plasma DXFs from the SAME sketches as the solids — no fit drift vs CAM.
    from build123d import Unit
    from build123d.exporters import ExportDXF
    for panel_name, sk in (
        ("face", panel_sketch(art, pilots=True)),
        ("middle", panel_sketch(None, pilots=True)),
    ):
        exporter = ExportDXF(unit=Unit.IN)
        exporter.add_shape(sk)
        dxf_path = OUT_STEP.parent / dxf_name(panel_name)
        exporter.write(str(dxf_path))
        print(f"wrote {dxf_path.name}")

    # One-page drill map for the bench — regenerated every run, in writing.
    panel_holes = [(x, y, "A") for x, y in corner_pattern()] + [
        (x, y, "B") for x, y in rivet_pattern()
    ]
    frame_holes = [(x, y, "C") for x, y in corner_pattern()] + [
        (x, y, "D") for x, y in rivet_pattern()
    ]
    map_path = drill_map(
        parts=[
            {"name": "face (art side up)", "width": W, "height": H, "corner_r": CORNER_R, "holes": panel_holes},
            {"name": "middle", "width": W, "height": H, "corner_r": CORNER_R, "holes": panel_holes},
            {"name": "frame (weldment)", "width": W, "height": H, "corner_r": CORNER_R,
             "holes": frame_holes, "window": (W - 2 * BAR, H - 2 * BAR)},
        ],
        refs={
            "A": f'drill {frac(BOLT_CLEAR_DIA)}" ({BOLT_CLEAR_DIA:.3f}) — bolt clearance, face+middle (from {frac(PILOT_DIA)}\" plasma pilot)',
            "B": f'drill {frac(RIVET_HOLE_DIA)}" ({RIVET_HOLE_DIA:.3f}) — solid rivet, face+middle (from {frac(PILOT_DIA)}\" plasma pilot)',
            "C": f'drill {frac(TAP_DRILL_DIA)}" ({TAP_DRILL_DIA:.3f}) → tap {BOLT} — frame corners  [same bit as B]',
            "D": f'drill {frac(RELIEF_DIA)}" ({RELIEF_DIA:.3f}) — rivet shop-head relief, frame',
        },
        out_path=OUT_STEP.parent / DRILLMAP_NAME,
        title=f"Bonebrake Cover — Drill Map  (Rev {REV}, {W:.2f} x {H:.2f}"
              f"{' test coupon' if COUPON else ''})",
        note=f"Clamp face+middle and drill A/B pairs together. Frame brick-mount holes: drill + countersink on-site. Plasma pilots are {frac(PILOT_DIA)} nominal.",
    )
    print(f"wrote {Path(map_path).name}")
    bom_path = write_bom(OUT_STEP.parent / BOM_NAME)
    print(f"wrote {bom_path.name}")
    sheet_path = write_buildsheet(OUT_STEP.parent / BUILDSHEET_NAME)
    print(f"wrote {sheet_path.name}")
    cam_path = write_camsheet(OUT_STEP.parent / CAMSHEET_NAME, has_art=art is not None)
    print(f"wrote {cam_path.name}")

    asm = Compound(children=[frame, middle, face, *fasteners])
    asm.label = f"bonebrake-cover-{REV_TAG}"
    OUT_STEP.parent.mkdir(parents=True, exist_ok=True)
    export_step(asm, str(OUT_STEP))
    print(f"\nwrote {OUT_STEP}")
    print_cut_list()


if __name__ == "__main__":
    main()
