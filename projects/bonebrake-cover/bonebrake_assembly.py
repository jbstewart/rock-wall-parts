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
from math import hypot, radians, tan
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from build123d import (  # noqa: E402
    Align,
    Axis,
    Box,
    Circle,
    Cone,
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
    Vector,
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
# Site: jagged pipe channel in brick running floor to an OVERHANGING cap course.
# Side bars carry ALL brick bearing; top/bottom bars bridge the channel.
#
# Rev C follows Brian's site visit of 2026-10-11 and retires every Rev A/B hedge:
# the opening, the under-cap height and the floor condition are all MEASURED now.
# The leak repair took brick out for pipe access and the carpet was replaced
# afterwards, leaving a bare strip of concrete along the wall. The cover grew a
# BASE to fill that strip, and because the base eats into the floor-to-cap
# height, every vertical component got shorter. "Carpet hides shortfall at the
# floor" is no longer the install story — the unit now stands ON its own base.
# Run `python bonebrake_assembly.py coupon` for the texture/test coupon
# (outputs land in output/coupon/); default run = the real cover.
COUPON = len(sys.argv) > 1 and sys.argv[1] == "coupon"

# Revision letter — stamped into every output filename and document header, and
# carried by hand into Fusion program names / posted gcode (e.g. face-revA.gcode).
# Bump on any form/fit/function change: dimensions, hole sizes, patterns, material,
# finish callouts, artwork. Letters per ASME Y14.35: skip I, O, Q, S, X, Z; after
# Y comes AA, AB, … The BRIEF's "Current revision" line and history table must be
# updated with every bump — a generation check enforces the match.
REV = "D"

FRAME_T = 0.25         # flat-bar thickness — the frame AND each of the two base bars

if COUPON:
    W, H, BAR = 2.5, 6.25, 0.5
    OPENING_W, UNDER_CAP_H = 1.0, 999.0   # no site constraints on a coupon
    BARE_L = BARE_D = CARPET_H = 0.0      # and no floor base
    BASE_D = BASE_T = 0.0
    BOTTOM_GAP_MARGINS = ()
    TAPCON_H_FROM_FLOOR = ()
else:
    OPENING_W = 5.5        # widest brick gap anywhere — VERIFIED on site (was an estimate)
    UNDER_CAP_H = 41.6875  # 41-11/16: concrete floor -> underside of the brick cap
    CARPET_H = 1.25        # top of the new carpet+pad above the concrete
    BARE_L, BARE_D = 8.5, 1.5   # bare concrete strip: 8.5 along the wall x 1.5 into the room
    # Bare strip remaining left/right of the brick gap where it meets the floor.
    # The bottom gap is BARE_L minus these (4.25 wide, offset 1/8 off centre).
    BOTTOM_GAP_MARGINS = (2.0, 2.25)
    BASE_D = BARE_D        # 1.5 into the room — the base fills the strip front to back
    BASE_T = 2 * FRAME_T   # 0.5 tall: two 1/4 x 1-1/2 bars laid flat and plug-welded
    W = BARE_L             # 8.5 — cover width MATCHES the base (Brian, on site)
    H = 41.125             # EVERY vertical component; BASE_T + H = 41.625 finished
    BAR = 1.5              # flat-bar width
    # Frame -> brick anchor heights above the CONCRETE floor, located on site.
    TAPCON_H_FROM_FLOOR = (5.0, 20.0, 40.0)

TOTAL_H = BASE_T + H   # floor to the top of the cover, as installed
CENTERING_TOL = 0.25   # how far off-centre in the channel the cover may land
PANEL_T = 0.125        # 11ga modeled at nominal 1/8 (actual 0.1196 runs safe-shy)
PANEL_MATERIAL = "11ga mild steel"   # shown in the program table Jimmie cuts from
# Coupon cuts 2 middles: one per candidate gray texture (engine-turned vs
# stone-texture can) for Michelle's finish choice. Real cover needs only 1.
PANEL_QTY = {"face": 1, "middle": 2 if COUPON else 1}
CORNER_R = 0.125       # face/middle corner radius

BOLT = "5/16-18"       # corner bolts: flanged button head hex, 5/16-18 x 1/2 —
# Rev B: sourced at the local hardware store; Brian judged 5/16 heads better
# proportioned on the 1.5" bar than the original 1/4-20 (91355A081, superseded).

BOLT_FLANGE_DIA = 0.69   # approximate — catalog STEP supersedes primitive dims
BOLT_DOME_DIA = 0.55
BOLT_HEAD_H = 0.20
BOLT_LEN = 0.5           # 1/2" = flush with frame back at nominal stack (0.500)
                         # VERIFY purchased length — anything longer fails the brick check

# Catalog hardware (McMaster STEP downloads) — used when the file exists in
# lib/hardware/, else the parametric primitive below stands in. Convention for
# both: origin at the head's bearing plane, shank pointing -Z. Tune each
# model's rotate/z_shift once after downloading (catalog orientations vary).
# Filename convention: <type>-<head/drive>-<thread>x<length>-<finish>-<sku>.step
# Config matches on the spec prefix (glob) so finish/SKU need no code change.
BOLT_MODEL = {"file": "bolt-flangedbutton-hex-5_16-18x1_2-*.step", "rotate_x": 0.0, "z_shift": 0.0}
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
# the published fractional equivalent. A and D now share one 11/32 bit (Rev B).
BOLT_CLEAR_DIA = 11 / 32   # 0.344 — bolt clearance (+0.031 over 5/16 major, rounds UP)
RIVET_HOLE_DIA = 13 / 64   # 0.203 — solid-rivet snug fit (shank swells to fill)
TAP_DRILL_DIA = 17 / 64    # 0.266 — 5/16-18 fractional tap equivalent (~65% thread, hand-tap friendly)

# --- Frame -> brick anchors. Through Rev B these were "installer's choice, on
# site, NOT in fab outputs". Brian located them against the actual brick on
# 2026-10-11, so Rev C generates them like every other hole: on the side-bar
# centreline, at 5 / 20 / 40 inches above the concrete.
TAPCON = '1/4" x 1-1/4" flat Phillips'
TAPCON_LEN = 1.25
TAPCON_MAJOR_DIA = 0.250        # THREAD CREST — the hole in our steel must pass this
TAPCON_HEAD_DIA = 0.500         # 1/4 flat head, 82-deg included
TAPCON_CSK_ANGLE = 82.0
TAPCON_MASONRY_PILOT = 0.1875   # 3/16 carbide, SDS
# Brian asked for 1/4" holes. A 1/4" hole will NOT pass a 1/4" Tapcon — the
# screw cuts its thread in the BRICK, not in our frame, so the frame hole is a
# clearance hole and clearance rounds UP. 9/32 is also what Rev A/B called for
# on the same screw. There is a check on this below.
TAPCON_CLEAR_DIA = 9 / 32       # 0.281
TAPCON_CSK_DIA = TAPCON_HEAD_DIA   # countersink to full head dia -> head finishes flush
TAPCON_CSK_DEPTH = (TAPCON_CSK_DIA - TAPCON_CLEAR_DIA) / 2 / tan(radians(TAPCON_CSK_ANGLE / 2))

# --- Floor base (Rev C). Two bars layered; the LOWER one carries the plug-weld
# holes so the upper bar's top face stays clean — the frame and the panel unit
# both seat on it, and any weld spatter there would hold them off the brick.
PLUG_DIA = 9 / 16    # AWS D1.1 plug-weld minimum for 1/4 plate is t + 5/16
PLUG_INSET = 0.75    # from the bar ends — the same 3/4 inset every other hole uses
BASE_ROUND = 0.125   # round-over on the base's exposed top arrises (Brian promised a toe break)


def frac(d: float) -> str:
    from fractions import Fraction
    f = Fraction(d).limit_denominator(64)
    return f"{f.numerator}/{f.denominator}"

OUT_DIR = Path(__file__).parent / "output" / ("coupon" if COUPON else "")
BASENAME = "bonebrake-coupon" if COUPON else "bonebrake"
REV_TAG = f"rev{REV}"          # filename form; documents print "Rev A"
OUT_STEP = OUT_DIR / f"{BASENAME}-assembly-{REV_TAG}.step"
DRILLMAP_NAME = f"{BASENAME}-drillmap-{REV_TAG}.pdf"
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

# Cut DENSITY limits (added Rev C, 2026-10-15, after Brian spotted cuts "within
# 1/8" on the face). Two different failure modes, two different floors:
#
#   WEB    — steel LEFT between two cuts. Plasma practice is a web of at least
#            1x material thickness; below that the land is heated from both
#            sides, can't sink it, and warps or blows through. On a 41" panel
#            that distortion accumulates and the face stops sitting flat on the
#            frame. 11ga is 0.1196 actual, so the floor is 0.1196 — NOT the
#            0.125 nominal we model, which is the trap: 1/8 reads as safe and
#            is not.
#   SLIVER — a finger of material being cut AWAY. Both passes offset into it,
#            so it loses a full kerf of width; under 2x kerf the two kerfs meet
#            and the detail opens ragged or disappears entirely.
#
# These are ARTWORK limits. Nothing in the parameter block can fix a violation:
# the art already fills 8.0 of the 8.5 panel, so it cannot be scaled up out of
# trouble. The fix is the source SVG.
PANEL_T_ACTUAL = 0.1196      # 11ga measured; PANEL_T above is the 1/8 we model
MIN_WEB = PANEL_T_ACTUAL
MIN_SLIVER = 2 * PLASMA_KERF
#
# HOW it is measured matters as much as the floors. The first attempt (2026-10-15)
# compared pairs of points on the cut contours and reported the smallest gap. That
# is WRONG for a tapered point of steel: its width goes to zero at the tip by
# definition, so "minimum width" measured that way is not a property of the part,
# it is a property of how far back from the tip you happen to sample. It reported
# a 24% regression on an artwork edit that was in fact a 7.5% improvement.
#
# So: rasterise, then ERODE by floor/2. Everything thinner than the floor
# disappears; what disappeared is the answer, and it is stable under reshaping.
# A tapered tip leaves a small patch (cosmetic — plasma cannot hold a knife edge).
# A long parallel-sided ribbon leaves a long patch, and THAT is the scrap risk,
# because a ribbon has no adjacent metal to sink the arc heat into. The gate is
# therefore on ribbon LENGTH, with total too-thin area reported as the trend.
RASTER_PITCH = 0.005         # measurement resolution
RIBBON_MIN_AREA = 0.004      # below this a patch is a whisker tip, not a ribbon
MAX_THIN_RUN = 8 * PANEL_T_ACTUAL   # 0.957 — longest tolerable run of too-thin

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

# Rev B (coupon lesson): the coupon's BAR/2 inset put rivet holes too close to
# the edge to drill their frame reliefs. Real cover locks EVERY fastener center
# at >= 3/4" from the panel edges (generation check); the coupon keeps its
# historical geometry — it's already cut.
EDGE_INSET = BAR / 2 if COUPON else 0.75
CORNER_INSET = EDGE_INSET


# Rev C — ONE uniform fastener pitch down each side bar. There are
# SIDE_STATIONS positions from corner to corner; BOLTS_PER_SIDE of them are
# bolts (always including both corners) and the rest are rivets, so the visible
# rhythm down the edge is identical whichever way Brian's 6-vs-8 question lands
# — only which dots are bolt heads changes.
SIDE_STATIONS = 7
BOLTS_PER_SIDE = 4      # 4 -> 8 bolts / 6 rivets (Rev C); 3 -> 6 bolts / 8 rivets
MAX_BOLT_PITCH = 15.0   # cosmetic edge-gap limit — see the bolt-pitch check.
                        # This encodes the 8-bolt decision, not a law of nature:
                        # dropping to 3 bolts/side gives a 19.8" pitch, so raise
                        # this WITH a note if you make that trade.

RIVET_SPACING_TARGET = 8.0   # coupon only — the real cover uses the station grid
RIVET_ROWS = 2 if COUPON else None


def side_stations() -> list[float]:
    """Fastener station heights down one side bar, top corner to bottom."""
    y_top = H / 2 - CORNER_INSET
    return [y_top - 2 * y_top * i / (SIDE_STATIONS - 1) for i in range(SIDE_STATIONS)]


def bolt_stations() -> list[int]:
    """Station indices that get a bolt — evenly spread, both corners included."""
    step = (SIDE_STATIONS - 1) / (BOLTS_PER_SIDE - 1)
    return [round(i * step) for i in range(BOLTS_PER_SIDE)]


def corner_pattern() -> list[tuple[float, float]]:
    """Bolt positions. "corner" is historical — through Rev B there were only
    four, one per corner. Rev C adds intermediate bolts down each side: four
    corners alone left a 39.6" unsupported run where the panel edge can stand
    off the frame and show a gap (Brian, on site)."""
    x = W / 2 - CORNER_INSET
    if COUPON:
        y = H / 2 - CORNER_INSET
        return [(-x, y), (x, y), (-x, -y), (x, -y)]
    ys = side_stations()
    return [(sx, ys[i]) for i in bolt_stations() for sx in (-x, x)]


def rivet_pattern() -> list[tuple[float, float]]:
    """Rivets take every station the bolts don't."""
    x = W / 2 - EDGE_INSET
    if COUPON:
        y_top = H / 2 - CORNER_INSET
        step = 2 * y_top / (RIVET_ROWS + 1)
        return [(sx, -y_top + step * (i + 1)) for i in range(RIVET_ROWS) for sx in (-x, x)]
    taken = set(bolt_stations())
    ys = side_stations()
    return [(sx, ys[i]) for i in range(SIDE_STATIONS) if i not in taken for sx in (-x, x)]


def tapcon_pattern() -> list[tuple[float, float]]:
    """Frame -> brick anchors, on the side-bar centreline. Brian gave the
    heights off the CONCRETE, so the base thickness comes out before converting
    to frame-local Y (5" off the floor is 4.5" off the frame's bottom edge)."""
    if COUPON:
        return []
    x = W / 2 - BAR / 2
    return [(sx, h - BASE_T - H / 2) for h in TAPCON_H_FROM_FLOOR for sx in (-x, x)]


def plug_pattern() -> list[float]:
    """Plug-weld hole X positions — LOWER base bar only, on its centreline."""
    if COUPON:
        return []
    return [-(W / 2 - PLUG_INSET), 0.0, W / 2 - PLUG_INSET]


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
        + [(p, RELIEF_DIA) for p in rivet_pattern()]
        + [(p, TAPCON_CLEAR_DIA) for p in tapcon_pattern()],
    )
    solid = extrude(sk, FRAME_T)
    # Tapcon countersinks are cut into the BACK face (z=0, the brick side) so
    # the flat heads finish flush and the frame still seats flat on the brick.
    for px, py in tapcon_pattern():
        solid -= Pos(px, py, TAPCON_CSK_DEPTH / 2) * Cone(
            TAPCON_CSK_DIA / 2, TAPCON_CLEAR_DIA / 2, TAPCON_CSK_DEPTH
        )
    solid.label = "frame"
    return solid


def base_bar(lower: bool):
    """One 1/4 x 1-1/2 bar of the floor base, built at the origin lying flat:
    x centred on W, y [0, FRAME_T] (it is only FRAME_T TALL), z [0, BASE_D]
    with z=0 at the brick face.

    The lower bar carries the plug-weld holes; the upper bar carries the
    round-over, because its top face is the one anyone can see or kick.
    """
    bar = Box(W, FRAME_T, BASE_D, align=(Align.CENTER, Align.MIN, Align.MIN))
    if lower:
        for px in plug_pattern():
            bar -= (Pos(px, FRAME_T / 2, BASE_D / 2) * Rot(90, 0, 0)
                    * Cylinder(PLUG_DIA / 2, 3 * FRAME_T))
        return bar
    # Break the arrises a toe could find: front edge and both ends, top only.
    # The back edge is against the brick and the bottom is on the concrete.
    exposed = [
        e for e in bar.edges()
        if abs(e.center().Y - FRAME_T) < 1e-6 and abs(e.center().Z) > 1e-6
    ]
    return fillet(exposed, BASE_ROUND)


def tapcon_primitive():
    """Flat-head masonry screw as installed: head seated in the frame's
    countersink (flush at z=0), shank running -Z into the brick. Cosmetic —
    there is no McMaster STEP for a Tapcon, and it is a purchased consumable.
    """
    head = Pos(0, 0, TAPCON_CSK_DEPTH / 2) * Cone(
        TAPCON_CSK_DIA / 2, TAPCON_CLEAR_DIA / 2, TAPCON_CSK_DEPTH
    )
    shank = Pos(0, 0, -TAPCON_LEN / 2) * Cylinder(TAPCON_MAJOR_DIA / 2, TAPCON_LEN)
    return head + shank


IN = 25.4  # STEP is mm; parts are scaled at origin then placed in mm.


# STEP carries flat RGB colors (not Fusion Appearances) — bake them here so
# every re-import arrives pre-tinted and appearance work isn't redone.
COLORS = {
    "frame": Color(0.10, 0.10, 0.10),   # black
    "middle": Color(0.62, 0.62, 0.62),  # light/medium gray contrast behind art
    "face": Color(0.10, 0.10, 0.10),    # black
    "screw": Color(0.13, 0.13, 0.13),   # black oxide
    "rivet": Color(0.80, 0.80, 0.82),   # aluminum
    "base-lower": Color(0.10, 0.10, 0.10),   # same hammered black as the frame
    "base-upper": Color(0.10, 0.10, 0.10),
    "tapcon": Color(0.45, 0.47, 0.50),       # bare masonry screw, installed last
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


def art_finals() -> list[Path]:
    """Artwork files the real cover would accept. artwork_face() takes [0], which
    is ALPHABETICAL, not newest — so two candidates is a silent-wrong-art trap
    (ArtLayer-Final-Rev-02 sorts before -Rev-03). A check enforces exactly one.
    """
    return sorted(
        f for f in ART_DIR.iterdir()
        if "final" in f.stem.lower() and f.suffix.lower() in (".dxf", ".svg")
    )


def artwork_face():
    """The art as a single Face, scaled and centered onto the panel — or None."""
    if COUPON:
        art_file = ART_DIR / "ArtLayer.dxf"
        if not art_file.exists():
            return None
    else:
        finals = art_finals()
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
    # hex-drive recess: cosmetic hexagonal pocket (3/16 across flats for 5/16 button)
    hex_af = 0.1875
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


def thin_features(art) -> dict:
    """Material and art detail too fine for the plasma process, by erosion.

    Two regions, two floors: the STEEL must hold MIN_WEB (1x thickness), the
    CUT-AWAY art must hold MIN_SLIVER (2x kerf) or the kerfs meet and the detail
    opens ragged. Both are measured the same way — rasterise, erode by floor/2,
    and look at what the erosion removed. See the note at RASTER_PITCH for why
    this replaced contour-pair sampling.

    Locations are reported BOTH in panel inches and as (u, v) normalised to the
    artwork's bounding box with the origin at LOWER LEFT, because an SVG carries
    no dimensions and (u, v) is the only thing that survives the round trip.
    """
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage

    abb = art.bounding_box()
    face = max(panel_sketch(art, pilots=True).faces(), key=lambda f: f.area)
    x0, y0 = -W / 2, -H / 2
    nx, ny = int(W / RASTER_PITCH), int(H / RASTER_PITCH)

    def poly(wire, step=0.004):
        pts = []
        for e in wire.edges():
            n = max(2, int(e.length / step))
            for i in range(n):
                q = e.position_at(i / n)
                pts.append(((q.X - x0) / RASTER_PITCH, (q.Y - y0) / RASTER_PITCH))
        return pts

    def raster(fill_faces):
        img = Image.new("1", (nx, ny), 0)
        dr = ImageDraw.Draw(img)
        for f in fill_faces:
            dr.polygon(poly(f.outer_wire()), fill=1)
            for w in f.inner_wires():
                dr.polygon(poly(w), fill=0)
        return np.array(img, dtype=bool)

    def ribbons(mask, floor):
        """Patches of `mask` thinner than `floor`, via an opening by floor/2."""
        r = floor / 2
        core = ndimage.distance_transform_edt(mask) * RASTER_PITCH >= r
        opened = ndimage.distance_transform_edt(~core) * RASTER_PITCH <= r
        thin = mask & ~opened
        lab, n = ndimage.label(thin)
        rows = []
        if n:
            d = ndimage.distance_transform_edt(mask) * RASTER_PITCH
            areas = ndimage.sum(thin, lab, range(1, n + 1)) * RASTER_PITCH ** 2
            for i in range(n):
                if areas[i] < RIBBON_MIN_AREA:
                    continue
                m = lab == (i + 1)
                ys, xs = np.nonzero(m)
                px = xs.mean() * RASTER_PITCH + x0
                py = ys.mean() * RASTER_PITCH + y0
                t = 2 * d[m].max()
                rows.append({
                    "area": float(areas[i]),
                    "len": float(areas[i] / max(t, 1e-6)),
                    "thick": float(t),
                    "x": float(px), "y": float(py),
                    "u": float((px - abb.min.X) / abb.size.X),
                    "v": float((py - abb.min.Y) / abb.size.Y),
                })
        rows.sort(key=lambda z: -z["len"])
        return rows, float(thin.sum() * RASTER_PITCH ** 2), int(n)

    steel = raster([face])
    cutaway = raster(art.faces())
    w_rows, w_area, w_n = ribbons(steel, MIN_WEB)
    s_rows, s_area, s_n = ribbons(cutaway, MIN_SLIVER)
    longest = lambda rows: rows[0]["len"] if rows else 0.0
    return {
        "webs": w_rows, "slivers": s_rows,
        "web_thin_area": w_area, "sliver_thin_area": s_area,
        "web_patches": w_n, "sliver_patches": s_n,
        "longest_web_run": longest(w_rows),
        "longest_sliver_run": longest(s_rows),
        "steel_area": float(steel.sum() * RASTER_PITCH ** 2),
        "cut_area": float(cutaway.sum() * RASTER_PITCH ** 2),
    }


def min_tapcon_gap() -> float:
    """Closest edge-to-edge distance from a Tapcon countersink to any other
    hole in the frame. Rev B let the installer eyeball these; Rev C fixes them,
    so proving they don't collide is now our job, not his."""
    others = ([(p, TAP_DRILL_DIA) for p in corner_pattern()]
              + [(p, RELIEF_DIA) for p in rivet_pattern()])
    gaps = [
        hypot(px - ox, py - oy) - TAPCON_CSK_DIA / 2 - od / 2
        for px, py in tapcon_pattern()
        for (ox, oy), od in others
    ]
    return min(gaps) if gaps else 999.0


def max_bolt_pitch() -> float:
    """Longest run of panel edge between two bolts."""
    ys = sorted({py for _, py in corner_pattern()})
    return max(b - a for a, b in zip(ys, ys[1:])) if len(ys) > 1 else 0.0


def bar_bearing_off_centre() -> float:
    """Brick still under the narrow-side bar when the cover lands
    CENTERING_TOL off centre in the channel."""
    intrude = max(0.0, OPENING_W / 2 + CENTERING_TOL - (W / 2 - BAR))
    return BAR - intrude


def run_checks(art=None) -> list[tuple[str, bool, str]]:
    cuts = thin_features(art)
    clamped = 2 * PANEL_T
    d = SOLID["shank_dia"]
    tail_ratio = (RIVET_LEN - clamped) / d
    bar_x_min = W / 2 - BAR  # inner edge of side bar
    checks = [
        ("window exists (W)", W - 2 * BAR > 0, f"window W = {W - 2 * BAR:.3f}"),
        # Rev B demanded a further 0.25 of bar past the widest jag. That margin
        # was a hedge against an ESTIMATED opening; the opening is now measured
        # (5.5 max) and the cover width is no longer free — it is set by the
        # bare carpet strip the base has to fill. CONSCIOUSLY RELAXED to "fully
        # on brick when centred", with the hedge re-expressed as the honest
        # physical quantity it was standing in for: bearing retained when the
        # cover lands off centre (next check).
        (
            "side bars land fully on brick when centred",
            W / 2 - BAR >= OPENING_W / 2,
            f"bar inner edge {W / 2 - BAR:.3f} >= widest jag {OPENING_W / 2:.3f}",
        ),
        (
            f"side bar keeps >= 1.0 of brick at {CENTERING_TOL:.2f} off centre",
            COUPON or bar_bearing_off_centre() >= 1.0,
            "coupon: no site constraints" if COUPON else
            f"{bar_bearing_off_centre():.2f} of the {BAR:.2f} bar still on brick",
        ),
        (
            "cover + base clears the cap lip",
            TOTAL_H <= UNDER_CAP_H,
            f"base {BASE_T:.3f} + verticals {H:.3f} = {TOTAL_H:.4f} "
            f"<= under-cap {UNDER_CAP_H:.4f}",
        ),
        (
            "top gap under the cap stays >= 1/16 (install slack)",
            COUPON or UNDER_CAP_H - TOTAL_H >= 1 / 16 - 1e-9,
            "coupon: n/a" if COUPON else
            f"top gap {UNDER_CAP_H - TOTAL_H:.4f} >= {1 / 16:.4f}",
        ),
        # The cap OVERHANGS, so the unit has to get its top in underneath. With
        # the base welded on, the binding dimension is the diagonal from the
        # base's front-bottom corner to the frame's top-back corner — if that
        # exceeds the opening the unit cannot be tilted in at all and the only
        # install path left is lifting it dead vertical and sliding it back.
        (
            "assembly can be tilted in under the overhanging cap",
            COUPON or hypot(BASE_D, TOTAL_H) <= UNDER_CAP_H,
            "coupon: n/a" if COUPON else
            f"max diagonal {hypot(BASE_D, TOTAL_H):.4f} (base front-bottom -> top-back) "
            f"<= under-cap {UNDER_CAP_H:.4f}, spare {UNDER_CAP_H - hypot(BASE_D, TOTAL_H):.4f}",
        ),
        (
            "base fills the bare concrete strip",
            COUPON or (W == BARE_L and BASE_D == BARE_D),
            "coupon: no base" if COUPON else
            f"base {W:.2f} x {BASE_D:.2f} = bare strip {BARE_L:.2f} x {BARE_D:.2f}",
        ),
        (
            "base finishes below the carpet (no toe to stub)",
            COUPON or BASE_T < CARPET_H,
            "coupon: no base" if COUPON else
            f"base {BASE_T:.2f} tall vs {CARPET_H:.2f} carpet — top sits "
            f"{CARPET_H - BASE_T:.2f} below the pile",
        ),
        (
            "side bars still find brick where the gap meets the floor",
            COUPON or min(BOTTOM_GAP_MARGINS) >= BAR,
            "coupon: n/a" if COUPON else
            f"bottom gap {W - sum(BOTTOM_GAP_MARGINS):.2f} wide, brick margins "
            f"{BOTTOM_GAP_MARGINS[0]:.2f}/{BOTTOM_GAP_MARGINS[1]:.2f} >= bar {BAR:.2f}",
        ),
        (
            "plug-weld holes meet the AWS D1.1 minimum for 1/4 plate",
            COUPON or PLUG_DIA >= FRAME_T + 5 / 16 - 1e-9,
            "coupon: no base" if COUPON else
            f"plug {frac(PLUG_DIA)} >= t + 5/16 = {FRAME_T + 5 / 16:.4f}",
        ),
        (
            "plug-weld holes leave metal all round",
            COUPON or (
                min(BASE_D / 2, W / 2 - max(abs(p) for p in plug_pattern())) - PLUG_DIA / 2 >= 0.25
                and min(abs(a - b) for a in plug_pattern() for b in plug_pattern() if a != b)
                >= 4 * PLUG_DIA
            ),
            "coupon: no base" if COUPON else
            f"edge metal "
            f"{min(BASE_D / 2, W / 2 - max(abs(p) for p in plug_pattern())) - PLUG_DIA / 2:.3f}"
            f" >= 0.25, pitch "
            f"{min(abs(a - b) for a in plug_pattern() for b in plug_pattern() if a != b):.2f}"
            f" >= 4d {4 * PLUG_DIA:.2f}",
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
            f"rivet x ±{W / 2 - EDGE_INSET:.3f}, bar inner edge ±{bar_x_min:.3f}",
        ),
        (
            "fastener centers >= 3/4 from panel edges (coupon relief lesson)",
            COUPON or (
                CORNER_INSET >= 0.75
                and EDGE_INSET >= 0.75
                and all(H / 2 - abs(py) >= 0.75 for _, py in rivet_pattern())
            ),
            "coupon exempt (already cut)" if COUPON else
            f"corner inset {CORNER_INSET:.2f}, rivet x inset {EDGE_INSET:.2f}, "
            f"rivet y edge dist {min(H / 2 - abs(py) for _, py in rivet_pattern()):.2f}",
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
        # Found 2026-10-15 while the art was mid-swap: the auto-pick is
        # alphabetical, so a second "final" file can silently win over the newer
        # one. Cheap to prove, expensive to discover on a cut panel.
        (
            "exactly one artwork 'final' candidate",
            COUPON or len(art_finals()) == 1,
            "coupon uses ArtLayer.dxf" if COUPON else
            f"{len(art_finals())} candidate(s): "
            f"{', '.join(f.name for f in art_finals()) or 'NONE'}"
            + (" — artwork_face() takes the ALPHABETICALLY first; "
               "leave exactly one in artwork/" if len(art_finals()) != 1 else ""),
        ),
        # Rev C, 2026-10-15. Brian flagged cuts "within 1/8" on the face; the
        # first version of these checks measured minimum contour-pair gaps and
        # was wrong on tapers (see the note at RASTER_PITCH). Rewritten to gate
        # on the length of a too-thin RUN, which is the physical scrap risk:
        # a ribbon has no adjacent metal to sink the arc heat. Do NOT raise
        # MAX_THIN_RUN to get a build out — it is a process limit, and the way
        # to confirm it is a coupon, not a looser number.
        (
            f"no run of steel thinner than {MIN_WEB:.4f} longer than {MAX_THIN_RUN:.3f}",
            cuts["longest_web_run"] <= MAX_THIN_RUN,
            f"longest {cuts['longest_web_run']:.3f}"
            + (f" at (u {cuts['webs'][0]['u']:.4f}, v {cuts['webs'][0]['v']:.4f}) "
               f"= panel ({cuts['webs'][0]['x']:+.3f},{cuts['webs'][0]['y']:+.3f}), "
               f"{cuts['webs'][0]['thick']:.4f} thick" if cuts["webs"] else "")
            + f"; {cuts['web_thin_area']:.4f} in2 of steel under floor "
              f"({100 * cuts['web_thin_area'] / cuts['steel_area']:.2f}%) in "
              f"{len(cuts['webs'])} ribbons",
        ),
        (
            f"no run of art thinner than {MIN_SLIVER:.3f} longer than {MAX_THIN_RUN:.3f}",
            cuts["longest_sliver_run"] <= MAX_THIN_RUN,
            f"longest {cuts['longest_sliver_run']:.3f}"
            + (f" at (u {cuts['slivers'][0]['u']:.4f}, v {cuts['slivers'][0]['v']:.4f}) "
               f"= panel ({cuts['slivers'][0]['x']:+.3f},{cuts['slivers'][0]['y']:+.3f}), "
               f"{cuts['slivers'][0]['thick']:.4f} wide" if cuts["slivers"] else "")
            + f"; {cuts['sliver_thin_area']:.4f} in2 of art under floor "
              f"({100 * cuts['sliver_thin_area'] / cuts['cut_area']:.2f}%) in "
              f"{len(cuts['slivers'])} ribbons",
        ),
        # Brian asked for 1/4" Tapcon holes; this is the check that catches it.
        (
            "Tapcon hole clears the screw's thread crest",
            TAPCON_CLEAR_DIA > TAPCON_MAJOR_DIA,
            f"hole {frac(TAPCON_CLEAR_DIA)} ({TAPCON_CLEAR_DIA:.3f}) > crest "
            f"{TAPCON_MAJOR_DIA:.3f} — a 1/4 hole would bind on a 1/4 Tapcon",
        ),
        (
            "Tapcon countersink leaves bar under the head",
            FRAME_T - TAPCON_CSK_DEPTH >= 0.10,
            f"csk {TAPCON_CSK_DEPTH:.3f} deep in a {FRAME_T:.3f} bar leaves "
            f"{FRAME_T - TAPCON_CSK_DEPTH:.3f}",
        ),
        (
            "Tapcon heads finish flush (frame seats flat on brick)",
            TAPCON_CSK_DIA >= TAPCON_HEAD_DIA,
            f"csk dia {TAPCON_CSK_DIA:.3f} >= head dia {TAPCON_HEAD_DIA:.3f}",
        ),
        (
            "Tapcon holes sit wholly on the side bars",
            COUPON or all(
                W / 2 - BAR + TAPCON_CSK_DIA / 2 <= abs(px) <= W / 2 - TAPCON_CSK_DIA / 2
                for px, _ in tapcon_pattern()
            ),
            "coupon: n/a" if COUPON else
            f"csk spans {min(abs(px) for px, _ in tapcon_pattern()) - TAPCON_CSK_DIA / 2:.3f}"
            f"..{max(abs(px) for px, _ in tapcon_pattern()) + TAPCON_CSK_DIA / 2:.3f} "
            f"inside bar {W / 2 - BAR:.3f}..{W / 2:.3f}",
        ),
        (
            "Tapcon countersinks clear every other frame hole",
            COUPON or min_tapcon_gap() >= 1 / 16,
            "coupon: n/a" if COUPON else
            f"closest edge-to-edge gap {min_tapcon_gap():.3f} >= {1 / 16:.4f} "
            f"(tightest pair: top anchor vs top corner bolt)",
        ),
        # Anchor edge distance in masonry. Brian confirmed on site that there is
        # brick meat either side of the gap; this records how much the geometry
        # actually leaves, because Rev C's narrower cover halved it (W 9 -> 8.5
        # moved the anchors 0.25 inboard while the gap stayed 5.5 wide).
        (
            "Tapcon anchors land in brick clear of the gap",
            COUPON or min(abs(px) for px, _ in tapcon_pattern()) - OPENING_W / 2 >= 0.5,
            "coupon: n/a" if COUPON else
            f"anchor centre {min(abs(px) for px, _ in tapcon_pattern()):.2f} is "
            f"{min(abs(px) for px, _ in tapcon_pattern()) - OPENING_W / 2:.2f} outboard of the "
            f"widest jag — thin for masonry, confirm sound brick at each one",
        ),
        (
            "bolt pitch holds the panel edge down (Brian's 6-vs-8)",
            COUPON or max_bolt_pitch() <= MAX_BOLT_PITCH,
            "coupon: 4 corners" if COUPON else
            f"{len(corner_pattern())} bolts, max pitch {max_bolt_pitch():.2f} <= "
            f"{MAX_BOLT_PITCH:.1f} (3 bolts/side would be {H / 2 - CORNER_INSET:.2f})",
        ),
        (
            "every side station is a bolt or a rivet, never both",
            len({p for p in corner_pattern()} & {p for p in rivet_pattern()}) == 0
            and (COUPON or (SIDE_STATIONS - 1) % (BOLTS_PER_SIDE - 1) == 0),
            f"{len(corner_pattern())} bolts + {len(rivet_pattern())} rivets, "
            f"no shared positions",
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
    if not COUPON:
        print(f"BASE CUT LIST (Rev {REV}) — 0.25 x {BAR:g} flat bar, square ends")
        print(f"  2 pcs  {W:.3f} long  (lay flat, one on the other = {BASE_T:.3f} tall"
              f" x {BASE_D:.3f} deep)")
    print("DRILL SCHEDULE (frame, after welding):")
    for px, py in corner_pattern():
        print(f'  ({px:+.3f}, {py:+.3f})  drill {frac(tap)}" -> tap {BOLT}')
    for px, py in rivet_pattern():
        print(f'  ({px:+.3f}, {py:+.3f})  drill {frac(relief)}"  (shop-head relief)')
    for px, py in tapcon_pattern():
        print(f'  ({px:+.3f}, {py:+.3f})  drill {frac(TAPCON_CLEAR_DIA)}" + '
              f'{TAPCON_CSK_ANGLE:g}-deg csk to {TAPCON_CSK_DIA:.3f} dia on the BACK '
              f'(csk {TAPCON_CSK_DEPTH:.3f} deep)  (Tapcon -> brick)')
    if not COUPON:
        print("DRILL SCHEDULE (base, LOWER bar only):")
        for px in plug_pattern():
            print(f'  ({px:+.3f}, {0.0:+.3f})  drill {frac(PLUG_DIA)}"  (plug weld)')
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
    # Frame perimeter (miter long-points) plus the two base bars at Rev C.
    bar_run = 2 * (W + H) + (0 if COUPON else 2 * W)
    bar_buy = bar_run + 4 * 0.25         # + saw kerf/handling allowance
    bar_ft = bar_buy / 12
    sheet_sqft = 2 * W * H / 144
    bar_cost = cost("flat_bar_1_4x1_5", bar_ft)
    sheet_cost = cost("sheet_11ga", sheet_sqft)
    sheet_note = (f"2 pcs {W:.3f} x {H:.3f} = {sheet_sqft:.1f} sqft "
                  f"(~${sheet_cost:.0f}; nest together; art cut in face only)")
    rows = [
        ("Flat bar 1/4 x " + f'{BAR:.2g}"' + " mild steel",
         "frame" if COUPON else f"frame + base ({2 * W:.1f}\" of it is the base)",
         f'{bar_run:.1f}" net — buy ≥ {bar_buy:.0f}" ({bar_ft:.1f} ft, ~${bar_cost:.0f})',
         "steel supplier"),
        ("Sheet 11ga mild steel", "face + middle panels", sheet_note, "steel supplier"),
        (f"Bolt, {BOLT} x 1/2 flanged button head hex", "unit → frame",
         f"{len(corner_pattern())} (Rev C: {BOLTS_PER_SIDE}/side)",
         "local hardware store (sourced 2026-08-30)"),
        (f'Solid rivet, {RIVET_SIZE} x {RIVET_LEN:.2g}" brazier head, aluminum',
         "face+middle (bucked)", f"{len(rivet_pattern())} + spares",
         f"McMaster {catalog_sku(RIVET_MODEL)} / Amazon on hand"),
        (f"Tapcon {TAPCON} (masonry screw)", "frame → brick",
         f"{len(tapcon_pattern()) or 4} (box incl. "
         f"{frac(TAPCON_MASONRY_PILOT)} carbide pilot bit)", "hardware store"),
        ("Spray: hammered black (face + frame); satin light gray (middle)", "finish",
         "1 can each", "hardware store"),
    ]
    lines = [
        f"# Bonebrake Cover — BOM  (Rev {REV}, {W:.3f} x {H:.3f})",
        "",
        f"Generated by bonebrake_assembly.py at Rev {REV} — regenerate, don't hand-edit.",
        "",
        "| Item | Used for | Qty / stock | Source |",
        "|---|---|---|---|",
    ]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", f"Material cost (price book): bar ~${bar_cost:.2f} + sheet ~${sheet_cost:.2f} "
              f"= **~${bar_cost + sheet_cost:.0f}** (hardware/paint extra; prices in lib/materials.py)"]
    index = [f"{frac(RIVET_HOLE_DIA)} (B)", f"{frac(TAP_DRILL_DIA)} (C)",
             f"{frac(BOLT_CLEAR_DIA)} (A + D — one bit)"]
    if not COUPON:
        index += [f"{frac(TAPCON_CLEAR_DIA)} (E)",
                  f"{TAPCON_CSK_ANGLE:g}-deg countersink (E)",
                  f"{frac(PLUG_DIA)} (F)"]
    lines += ["", f"Drill index needed: {', '.join(index)}, {BOLT} tap; "
              f"on-site: {frac(TAPCON_MASONRY_PILOT)} carbide (SDS) only — Rev C drills and "
              f"countersinks the brick-mount holes in the SHOP."]
    out_path.write_text("\n".join(lines) + "\n")
    return out_path


# --------------------------------------------------------------- BUILD SHEET


def write_buildsheet(out_path: Path) -> Path:
    bolt_sku = catalog_sku(BOLT_MODEL)
    rivet_sku = catalog_sku(RIVET_MODEL)
    n_riv = len(rivet_pattern())
    n_bolt = len(corner_pattern())
    n_tap = len(tapcon_pattern())
    middles = PANEL_QTY["middle"]
    clamp_stack = ("face on middle" if middles == 1
                   else f"face on BOTH middles ({middles + 1}-sheet stack)")
    extra_middle_note = "" if middles == 1 else (
        "\n- BOTH middles get the full drill pattern — either can then be bolted into"
        "\n  the stack for texture photos; rivet only after the finish choice."
    )
    if COUPON:
        tapcon_bullet = "- No brick-mount holes on a coupon."
        base_section = ""
        install_section = "- Coupon — nothing to install."
    else:
        install_section = f"""- Site, in this order. The unit is a single weldment now (base welded to frame),
  so it goes in as one piece and there is only {UNDER_CAP_H - TOTAL_H:.4f}" of gap
  at the top when it is standing on its base. It will NOT swing in like a picture
  frame — lift it just clear of the floor, hold it plumb, and slide it straight
  back until the frame's back face meets the brick. Two people.
- Dry-fit FIRST, before drilling anything: confirm it stands in the channel with
  the base flat on the concrete and the top under the cap. If it fouls, find out
  why now — the fix is grinding the base, not the top.
- Base sits in the bare strip; the surrounding carpet is {CARPET_H:.2f}" so the
  base finishes {CARPET_H - BASE_T:.2f}" below the pile. Bed it on a bead of
  construction adhesive if the concrete is uneven — do NOT shim it up, that
  spends the top gap.
- Mark through the {n_tap} E holes, swing the unit out, SDS-drill the brick
  {frac(TAPCON_MASONRY_PILOT)} carbide, at least {TAPCON_LEN + 0.25:.2f}" deep;
  blow the dust out (dust is what strips Tapcons).
- Drive {n_tap}x Tapcon {TAPCON}. Heads must pull FLUSH into the shop-drilled
  countersinks — the panels seat against that face. Do not overdrive; a spun
  Tapcon in brick is done, move to a fresh hole in sound brick.
- The anchors sit only {min(abs(px) for px, _ in tapcon_pattern()) - OPENING_W / 2:.2f}"
  outboard of the widest part of the gap. Check each spot is solid brick or a
  sound mortar joint before you drill; relocate along the bar if one is crumbly.
- Frame + base are permanent. ALL future service is the {n_bolt} corner bolts.
- Hang the panel unit last: set its bottom edge down on the base top, tip it
  back against the frame, then run the {n_bolt} bolts."""
        tapcon_bullet = (
            f'- {n_tap}x E — brick-mount holes, NEW AT REV C (through Rev B these were '
            f'drilled\n'
            f'  on site by eye). Drill {frac(TAPCON_CLEAR_DIA)}" through, then '
            f'{TAPCON_CSK_ANGLE:g}-deg countersink to {TAPCON_CSK_DIA:.3f}" dia\n'
            f'  FROM THE BACK (brick side) — about {TAPCON_CSK_DEPTH:.3f}" deep. The flat '
            f'Tapcon heads\n'
            f'  must finish FLUSH or very slightly below that face: the frame seats on '
            f'brick there,\n'
            f'  and a proud head rocks the whole cover. Positions are on the drill map; '
            f'they are\n'
            f'  on the side-bar centreline at {", ".join(f"{h:g}" for h in TAPCON_H_FROM_FLOOR)}'
            f'" above the CONCRETE floor.'
        )
        base_section = f"""
## 1b. Floor base (Rev C — new)

Fills the bare strip of concrete left along the wall after the pipe repair: the
brick came out for access and the replacement carpet stops short of it. The base
is also what the whole cover now stands on, so its height is part of the fit.

Material: 1/4 x {BAR:.2g}" flat bar, 2 pcs {W:.3f}" long, square ends (no miters).

Requirements:
- LOWER bar only: {len(plug_pattern())}x F ({frac(PLUG_DIA)}") plug-weld holes on the bar
  centreline, at x {", ".join(f"{p:+.3f}" for p in plug_pattern())}".
- Lay the two bars flat, one on the other, edges flush all round. Plug-weld
  through the lower bar's holes — fill them. Grind those welds FLUSH to the
  bottom face so the base sits flat on concrete without rocking.
- The UPPER bar's top face is a seating surface — the frame AND the panel unit
  both land on it. Keep it clean and flat: no spatter, no proud weld, no grind
  dish.
- Round over the top front edge and both top ends to ~{BASE_ROUND:.3g}" R (flap
  disc). The back edge and the whole bottom are hidden — leave them.
- Finished base: {W:.3f}" long x {BASE_D:.3f}" deep x {BASE_T:.3f}" tall.
- Weld the base to the frame: the frame's bottom bar stands ON the base, its
  BACK face flush with the base's back edge (so {BASE_D - FRAME_T - 2 * PANEL_T:.2f}"
  of base projects forward of the finished cover face). Fillet weld the full
  {W:.3f}" seam along the front, where the frame's front face meets the base top.
  The back seam is against the brick — skip it.
- CRITICAL: the base top must end up square to the frame and the overall height
  must come out at {TOTAL_H:.3f}" or under. Floor-to-cap on site is
  {UNDER_CAP_H:.4f}" and there is only {UNDER_CAP_H - TOTAL_H:.4f}" of gap at the
  top. Check it with a tape before the panels go anywhere near it.
"""

    text = f"""# Bonebrake Cover — Build Sheet  (Rev {REV}, {W:.3f} x {H:.3f})

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
- Drill AFTER welding, per drill map: {n_bolt}x C ({frac(TAP_DRILL_DIA)}") -> tap {BOLT};
  {n_riv}x D ({frac(RELIEF_DIA)}") rivet reliefs. Positions on the drill map / drill schedule.
{tapcon_bullet}
{base_section}
## 2. Panels (from plasma blanks)

Plasma programs — what to cut, how many, and the blank each needs:

{program_table()}

Face (art cut in) + middle (plain), plasma-cut with {frac(PILOT_DIA)}" pilot holes.
- Clamp {clamp_stack}, art side up, edges flush. Drill pilot pairs TOGETHER:
  {n_bolt}x A ({frac(BOLT_CLEAR_DIA)}"), {n_riv}x B ({frac(RIVET_HOLE_DIA)}"). Deburr.{extra_middle_note}
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
- MASK the {n_bolt} tapped holes in the frame (paint in threads binds bolts —
  or chase threads after).
- The {n_tap} brick-mount countersinks ARE painted (they're drilled in the shop now).
  Paint in a countersink is fine — just don't let it build into a bump that holds
  the Tapcon head proud.
- Expect minor touch-up at rivet holes after bucking.

## 5. Fit-up + install

- Shop fit check: set riveted unit on the frame — shop heads drop into the D
  reliefs, unit sits FLAT. Run all {n_bolt} bolts ({BOLT} x 1/2 flanged button,
  {bolt_sku}) through A holes into the tapped holes. Snug only — 11ga under a
  flange, not a head gasket.
{install_section}"""
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
        f'Blank sizes are the part bbox ({W:.3f} x {H:.3f} exact) rounded up to the '
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
    text = f"""# Bonebrake Cover — CAM Sheet  (Rev {REV}, {W:.3f} x {H:.3f})

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
    extras = []
    if not COUPON:
        # The base hangs below the frame: lower bar on the concrete, upper bar
        # under the frame's bottom bar. Both built lying flat at the origin.
        extras.append(place(base_bar(lower=True), 0, -H / 2 - BASE_T, 0, "base-lower"))
        extras.append(place(base_bar(lower=False), 0, -H / 2 - FRAME_T, 0, "base-upper"))
        tapcon = tapcon_primitive()
        extras += [place(tapcon.scale(1.0), px, py, 0, f"tapcon{i}")
                   for i, (px, py) in enumerate(tapcon_pattern(), 1)]

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
    frame_holes = (
        [(x, y, "C") for x, y in corner_pattern()]
        + [(x, y, "D") for x, y in rivet_pattern()]
        + [(x, y, "E") for x, y in tapcon_pattern()]
    )
    map_parts = [
        {"name": "face (art side up)", "width": W, "height": H, "corner_r": CORNER_R, "holes": panel_holes},
        {"name": "middle", "width": W, "height": H, "corner_r": CORNER_R, "holes": panel_holes},
        {"name": "frame (weldment)", "width": W, "height": H, "corner_r": CORNER_R,
         "holes": frame_holes, "window": (W - 2 * BAR, H - 2 * BAR)},
    ]
    map_refs = {
        "A": f'drill {frac(BOLT_CLEAR_DIA)}" ({BOLT_CLEAR_DIA:.3f}) — bolt clearance, face+middle (from {frac(PILOT_DIA)}\" plasma pilot)',
        "B": f'drill {frac(RIVET_HOLE_DIA)}" ({RIVET_HOLE_DIA:.3f}) — solid rivet, face+middle (from {frac(PILOT_DIA)}\" plasma pilot)',
        "C": f'drill {frac(TAP_DRILL_DIA)}" ({TAP_DRILL_DIA:.3f}) → tap {BOLT} — frame, {len(corner_pattern())} places  [same bit as B]',
        "D": f'drill {frac(RELIEF_DIA)}" ({RELIEF_DIA:.3f}) — rivet shop-head relief, frame',
    }
    if not COUPON:
        # Base is drawn in PLAN (looking down): W along the wall, BASE_D into
        # the room. Only the lower bar is drilled.
        map_parts.append({
            "name": "base — LOWER bar, plan view", "width": W, "height": BASE_D,
            "corner_r": 0.0, "holes": [(x, 0.0, "F") for x in plug_pattern()],
        })
        map_refs["E"] = (f'drill {frac(TAPCON_CLEAR_DIA)}" ({TAPCON_CLEAR_DIA:.3f}) + '
                         f'{TAPCON_CSK_ANGLE:g}° countersink to {TAPCON_CSK_DIA:.3f} dia '
                         f'ON THE BACK FACE — Tapcon → brick, frame')
        map_refs["F"] = (f'drill {frac(PLUG_DIA)}" ({PLUG_DIA:.3f}) — plug-weld holes, '
                         f'base LOWER bar only')
    map_path = drill_map(
        parts=map_parts,
        refs=map_refs,
        out_path=OUT_STEP.parent / DRILLMAP_NAME,
        title=f"Bonebrake Cover — Drill Map  (Rev {REV}, {W:.3f} x {H:.3f}"
              f"{' test coupon' if COUPON else ''})",
        note=("Clamp face+middle and drill A/B pairs together. "
              + ("" if COUPON else
                 "E countersinks are cut from the BACK (brick side) — heads must finish flush. ")
              + f"Plasma pilots are {frac(PILOT_DIA)} nominal."),
    )
    print(f"wrote {Path(map_path).name}")
    bom_path = write_bom(OUT_STEP.parent / BOM_NAME)
    print(f"wrote {bom_path.name}")
    sheet_path = write_buildsheet(OUT_STEP.parent / BUILDSHEET_NAME)
    print(f"wrote {sheet_path.name}")
    cam_path = write_camsheet(OUT_STEP.parent / CAMSHEET_NAME, has_art=art is not None)
    print(f"wrote {cam_path.name}")

    asm = Compound(children=[frame, middle, face, *fasteners, *extras])
    asm.label = f"bonebrake-cover-{REV_TAG}"
    OUT_STEP.parent.mkdir(parents=True, exist_ok=True)
    export_step(asm, str(OUT_STEP))
    print(f"\nwrote {OUT_STEP}")
    print_cut_list()


if __name__ == "__main__":
    main()
