# Bonebrake Cover — Assembly Brief

Spec for `bonebrake_assembly.py`. The 2D single-panel test path lives in `bonebrake_cover.py`. All inches. Confirmed by Brian 2026-08-24.

## Datums

Origin = center of the frame's back face (the face touching the brick). X = width, Y = height, +Z = out of the brick. Frame occupies z [0, 0.25], middle [0.25, 0.375], face [0.375, 0.50].

## Stackup (brick → out)

| # | Layer | Material | Thickness | Fab |
|---|---|---|---|---|
| 3 | Frame | 0.25 × 1.5 flat bar, mitered + welded corners | 0.250 | saw + weld + drill/tap → **cut list + drill schedule** |
| 2 | Middle panel (contrast backer behind art — CONFIRMED 11ga, modeled at nominal 1/8) | 11ga | 0.125 | plasma → DXF |
| 1 | Face panel, ArtLayer artwork cut through | 11ga | 0.125 | plasma → DXF |

## Hardware & joints

- **Frame → brick:** 4× **Tapcon 1/4" × 1-1/4" flat Phillips head** masonry screws (DECIDED 2026-08-25, replacing threaded inserts — the frame is permanent, all service access is via the corner bolts, so Tapcons' limited re-drive cycles don't matter; Brian has an SDS hammer drill; 3/16 carbide pilot, 1"+ embedment). Frame holes drilled 9/32 + **countersunk 82° on-site** during install → mount holes are NOT in fab outputs (build sheet §4 has the full site procedure).
- **Face+middle (riveted unit):** 6× **3/16 × 1/2 aluminum SOLID rivets, brazier head** (Amazon on hand — 3/8 length also on hand is too short for a shop head, 0.67d tail; McMaster equivalent to follow), 3 per side, evenly spaced between the corner bolts. **Bucked on the bench** (unit has back-side access — blind/POP rejected: mandrel hole is ugly and blind capability is unneeded). Factory heads on the face; shop heads (~1.5d = 0.281 dia × 0.094 high) form on the middle's back and **nest into the frame's 0.340 relief holes**. Panel holes: drill #11 (0.191) — snug, the shank swells to fill. Clamped stack 0.250 nominal / 0.239 actual.
- **Unit → frame:** 4× **1/4"-20 × 1/2" black-oxide flanged button-head hex-drive bolts** (McMaster, alloy steel, pack of 25 @ $11.74 — SKU on the ordered pack; DECIDED 2026-08-24: dome+flange rhymes with the rivet heads, flange spreads clamp load on 11ga, hex won't cam out; coarse chosen over the 1/4-28 fine variant — standard tap, cheaper). Frame: tap drill #7 (0.201), **tapped 1/4-20** — 5 threads engaged. Face+middle: clearance 0.257 (close fit). 1/2" length is flush at the nominal 0.500 stack (actual 11ga runs ~0.011 safe-shy). Heads sit proud on the face. Render models: catalog STEPs in `lib/hardware/` when downloaded (download as 3-D STEP, not SolidWorks), parametric primitives otherwise.

## Finish (DECIDED 2026-08-25)

**Hammered black** rattle-can on face + frame (on-brand forged texture, hides grind marks/mill scale; powder coat quoted ~$100 — too rich for this client). Middle: light gray field, **textured — technique TBD**: leading options are engine-turned swirls + clear (drill press, kinetic shimmer through the cutouts) or gray stone-texture rattle can (easy, on-theme); rule: texture scale must stay fine, it only shows through cutout slivers. **Middle edges painted black** — no gray stripe on assembly sides. Etched topo-contour background = premium variant idea for a future RWM catalog version. Paint after drill/tap, before riveting; mask the tapped corner holes. Full procedure: build sheet §4.

## Patterns (named, single-source)

- `corner_pattern` — 4 pts at (±(W/2 − bar/2), ±(H/2 − bar/2)) — centered on the bar.
- `rivet_pattern` — x = ±(W/2 − bar/2); y = 3 evenly spaced positions between the corner screws per side.

## Parameters

W, H (real cover TBD; **test = 2.5 × 6.25 with bar = 0.5** — real bar = 1.5), thicknesses, corner radius, rivet length (1/2" — tail ratio checked at generation).

## Validation rules (checked at generation)

1. Window exists: W − 2·bar > 0 and H − 2·bar > 0.
2. Pattern XY identical across every layer a fastener passes through (by construction — verified anyway).
3. Rivet tail = 1.3–1.7d beyond the clamped stack (forms a proper shop head; 1/2" length = 1.33d ✓, 3/8" fails at 0.67d).
4. Shop head (1.5d dia × 0.5d high) clears the relief dia and hides inside frame thickness.
5. All pattern holes land fully on the frame bar (edge distance ≥ 2× hole dia where feasible).
6. No solid interference except fasteners-in-holes.

## Outputs

- STEP assembly, named components: `frame`, `middle`, `face`, `rivet[1..6]`, `screw[1..4]` (simplified solids).
- DXF for face and middle, exported from the same sketches as the 3D solids (art IS cut in the 3D face; placement auto-fit then kernel-backed-off until it provably clears every fastener keep-out — no hand-cutting in Fusion, no CAM/model drift). **Panel holes in the DXFs are 1/16" plasma PILOTS** — plasma can't cut clean holes near material thickness — drilled to final size per the panel drill schedule (clamp face+middle, drill pairs together for guaranteed alignment). The 3D solids show finished holes. `bonebrake_cover.py` (2D-only path) is superseded, kept for reference.
- Frame cut list: 4 bars (long-point lengths, 45° miters) + drill schedule (4× tap-drill #7 (0.201) → tap 1/4-20; 6× shop-head relief 0.340; brick-mount holes field-drilled/countersunk on-site).
- Drill map SVG (to-scale, lettered holes, fractional drill legend) + generated BOM (`bonebrake-bom.md` — SKUs parsed from `lib/hardware/` filenames, stock computed from geometry, drill-index manifest) + build sheet (`bonebrake-buildsheet.md` — weldment fab print w/ acceptance criteria, requirements not technique; panel drilling op; bench rivet assembly w/ orientations; fit-up + site install).
- Check report (13 checks).

## Open items

1. Middle panel material/finish/thickness confirmation.
2. Real cover W × H.
3. ~~Rivet SKU~~ RESOLVED: solid 3/16 × 1/2 aluminum brazier-head (ordered from Amazon; McMaster equivalent to follow — search "aluminum solid rivet 3/16 brazier/universal head 1/2"). Bucking tools needed at the bench: rivet set/dolly for the brazier head + hammer or squeezer. Project is INDOOR — galvanic/mandrel-rust concerns void.
