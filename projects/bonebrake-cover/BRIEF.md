# Bonebrake Cover — Assembly Brief

Spec for `bonebrake_assembly.py` (dual-config: default = real cover, `coupon` arg = test coupon → `output/coupon/`, self-named files). All inches. Current as of 2026-08-25.

Current revision: **A** — the script's `REV` must match this line (generation check); every output filename carries `revA`, and Fusion-posted gcode must be named to match. Bump on any form/fit/function change (dimensions, holes, patterns, material, finish, artwork); letters skip I O Q S X Z per ASME Y14.35. On release: attach new-rev files to the PPBO Job and remove the superseded ones. History at bottom.

## Site (Michelle Bonebrake, 887 W 330 S, Logan — indoor brick wall)

Jagged pipe channel floor-to-cap. The top cap course OVERHANGS: cover top must tuck under the lip (no slop up); carpet hides shortfall at the floor — install slides UP tight. Side bars carry ALL brick bearing (top/bottom bars bridge the channel). **VERIFY on site:** widest jag anywhere (≤5.5" keeps W=9) and minimum under-cap height at L/C/R (≥41.5 keeps H=41.25). Encoded as `OPENING_W` / `UNDER_CAP_H` with bearing + fit checks.

## Configurations

| | Real cover | Coupon (texture/demo) |
|---|---|---|
| W × H | **9 × 41.25** (provisional pending tape) | 2.5 × 6.25 |
| Bar | 1.5 | 0.5 |
| Art | `artwork/*final*` (SVG or DXF; ArtLayer.dxf = loud placeholder) | ArtLayer.dxf (single tree) |
| Rivets | **10** (5 pairs, ~6.6" pitch — matches concept render; set `RIVET_ROWS=3` for a 6-rivet variant, possible Michelle render-choice) | 4 (2 pairs) |
| Panels cut | 1 face + 1 middle | 1 face + **2 middles** (one per candidate gray texture for Michelle's pick) |

## Datums / stackup (brick → out)

Origin = center of frame back face; +Z out of brick. Frame 0.25×BAR flat bar, mitered + welded, outer corners radiused → z [0, 0.25]. Middle 11ga (nominal 1/8) gray → [0.25, 0.375]. Face 11ga black, art cut through → [0.375, 0.50].

## Hardware & joints (as-built sizes = fractional drill index, per-role rounding)

- **Frame → brick:** 4× Tapcon 1/4" × 1-1/4" flat Phillips (frame permanent; service = corner bolts; SDS on site). Frame: 9/32 + 82° countersink, drilled ON-SITE (positions installer's choice, side bars only — clear of C/D holes, 1"+ from brick edges). NOT in fab outputs.
- **Face+middle (riveted unit):** 3/16 × 1/2 aluminum SOLID brazier rivets (McMaster 97484A245 / Amazon on hand; 3/8-length fails tail check at 0.67d). Bucked on the bench — factory heads on face, shop heads (~0.281 × 0.094) nest in frame reliefs. Panel holes **13/64** (snug; shank swells). Tail = 1.33d ✓.
- **Unit → frame:** 4× 1/4-20 × 1/2 black-oxide flanged button-head hex (91355A081; flange = built-in washer for 11ga; coarse over 1/4-28: standard tap + cheaper). Panels: **9/32** clearance (rounds UP). Frame corners: tap drill **13/64** → tapped 1/4-20, 5 threads. Same 13/64 bit as the rivet holes. Flush at nominal 0.500 stack.
- Frame rivet reliefs: **11/32** (shop heads clear + hide inside bar).

## Finish (DECIDED)

Hammered black on face + frame (forge texture, hides mill scale; powder coat $100 = too rich). Middle: light gray field, **texture via Michelle's Customer Questionnaire** — options photographed on the coupon (engine-turned + clear vs gray stone-texture can); texture scale must stay fine (shows only through cutout slivers). Middle EDGES black. Rivet finish (bright vs blacked) = questionnaire Q2. Paint after drill/tap, before riveting; mask tapped holes.

## Plasma / CAM

Panel DXF holes are **1/8" PILOTS** (drilled to final per schedules; clamp face+middle, drill pairs together). Pilots cut via the **small-hole CAM recipe** (settings finalized 2026-08-25): separate holes-only 2D Profile op, Passes→Sideways Comp = CENTER, Linking tab: Leads→Lead-In (Entry) + Lead-Out (Exit) both UNCHECKED, Piercing→Pierce Clearance = 0 (normal comp refuses < ~3/16; default 0.059 pierce clearance can't fit). Art + outline = normal op. Kerf stays in CAM. Full per-op setup is the generated **CAM sheet** (`…-camsheet-revX.md`) — set up Fusion from it, not from memory.

## Validation (17 checks gate generation)

Window exists ×2 · side bars bear on brick past jag · cover fits under cap lip · rivet tail 1.3–1.7d · shop head hides in frame · shop head clears relief · rivet holes land on bar · bolt not into brick · ≥2 threads engaged · corner holes on bar · rivet snug fit (0 < slop ≤ 0.02) · bolt clearance clears major · pilot ≥ 2× kerf (center-comp recipe) · pilot ≤ smallest finish − 0.01 · artwork clears every fastener keep-out (kernel boolean, auto-backoff fit) · BRIEF current revision matches script `REV`.

## Outputs (one command per config)

STEP assembly (named + colored; Insert CAD into inch design) · face/middle DXFs from the same sketches (Unit.IN; Insert DXF w/ Units=Inch) · frame cut list (miter long-points) + drill schedule · panel drill schedule · drill-map PDF (lettered holes, fractional legend; PDF so it attaches to the PPBO Job as a document, not an image) · BOM (SKUs from lib/hardware filenames; material $ from lib/materials.py price book) · build sheet (fab print + traveler + finish + install §) · CAM sheet (Fusion op settings incl. small-hole recipe) · program table (gcode name / material / qty / blank W×H rounded UP to 1/2", in both CAM + build sheets) · check report.

## Open items

1. Site tape visit (Thu task in PPBO/rock-wall-forge): jag width, under-cap min, Michelle's email, coupon show-and-tell.
2. Michelle questionnaire: backer texture, rivet finish, (maybe) 10-vs-6 rivet renders.
3. Quote via PPBO after answers — 50% deposit, balance on install, ACH-preferred.

## Revision history

| Rev | Date | Change |
|---|---|---|
| A | 2026-08-25 | Initial release under revision control (design state as specified above: 9 × 41.25 provisional, 10 rivets, hammered black / gray texture TBD). |
