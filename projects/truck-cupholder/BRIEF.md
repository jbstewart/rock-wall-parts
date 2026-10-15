# Truck cup holder — BRIEF

Current revision: **G**

Replacement for the worn OEM dual cup holder insert in the fold-down center armrest of Brian's Silverado bench seat. 3D printed (PETG), personal part — no plasma/weld pipeline, no PPBO job. Source measurements: `MEASUREMENTS.md` (Brian, calipers, 2026-08-30) and `SilveradoCupHolder Drawing.pdf` (Brian's CAD of the foam recess).

## Problem

The OEM insert (shallow oval tray, ~1.75" bores) fails two ways: bores are too wide/shallow for the 30 oz tumblers actually used (tippy), and the four cantilever snap hooks that once retained it under the seat's embedded plastic plate have worn off flush — the insert lifts straight out.

## Architecture (DECIDED 2026-08-30)

Two-piece system, three unique printed parts (base ×1, collar ×2, clip ×4):

- **Base** (stays snapped into the platform): **one-piece stadium** plug matching the recess (Rev B — the recess is two circles JOINED BY A RECTANGLE per the drawing, not a bare circle union; Rev A's figure-8 pinched at the waist, exposing the recess mid-span on both sides) (the ~8.25"/211 mm flange fits the confirmed CR-6 SE bed; an earlier two-half split existed only for a feared 150 mm bed and was dropped 2026-08-30). Four cantilever snap hooks engage under the embedded plate (ramped both ways → removable with a firm pull, but it normally never comes out). **Rev C: the clips are separate parts, printed flat** — Casey's coupon test snapped an integral clip at its root (layer seams ran across the leg; unavoidable in any printable base orientation). Each clip's T-head drops into a pocket through the flange and bears on the plug wall; pull-out load seats the head deeper. Broken clip = a 10-minute reprint, and clip stiffness is tunable without touching the 9-hour base. Each bore is a shallow well (cup floor 0.55 below flange) with a drain hole.
- **Collar** (superstructure, quantity 2, identical parts): a ~3"-tall tapered tube per cup that supports the tumbler at its full taper-top diameter (3.5"). Each collar **bayonet twist-locks** into its well — lugs drop into entry slots near the outboard end, twist ~25° toward lock. To seat a third passenger: two quarter-ish twists, lift both collars, fold the platform; the base stays put.
- Collars are one part used twice: rotating the part 180° serves the mirrored position (lugs at 135°/315° are C2-symmetric; the waist-facing scallop swaps sides correctly).

Why not clone the OEM insert: it engaged the same plate but gave no tall cup support and its bores fit nothing we own; the clips get redesigned with fresh hooks since the OEM barbs wore off flush.

Why a relief notch on each collar: two 3.5" cups on 3.75" centers nearly touch. Rev A–D trimmed each collar by the neighbor's envelope (a "scallop" that read as a print defect — Brian); **Rev E replaces it with a deliberate U-shaped through-wall notch** (1.70 wide, bottom at z 1.55, round bottom) facing the other cup. It carries all waist clearance for the Rev E beefed wall (0.10 → 0.14, Casey), kernel-proven for a locked pair AND for dropping a second collar in beside a locked one.

## Key measurements adopted (and reconciliations)

- Recess: **stadium** — circles Ø3.96 on 3.75 centers joined by a full-height rectangle (7.71 × 3.96 overall, per drawing), depth 0.75. Fabric opening 7.75 × 4 (also a stadium). Flange coverage is kernel-verified everywhere, not bbox-compared (Rev A bug).
- Retention plate: 1/8 thick; **hook ledge (plate underside) at 0.50 below the flange seat** (Brian's corrected measurement 2026-08-30 — the worksheet's 11/32 + 1/16 entries superseded).
- **Fold constraint (2026-08-30): the base may stand no more than 1.25 above the fabric** or the platform won't fold into the seatback (generation check). Collars are exempt — they come off before folding.
- Clip pockets: 4 side pockets 1.0 wide, extending 0.38 radially past the hole edge, 0.5 deep below the plate. Drawing implies pocket c-c ≈3.5; worksheet says 3.75. **Hooks sit at c-c 3.625, 0.70 wide** — a generation check proves they land inside the pockets under BOTH interpretations. The drawing's small end notch (0.75 × 0.09) is unused.
- Flange thickness ~1/8 (Brian confirmed; the worksheet's 1.32 was the formed-flange height, a different feature). New flange 0.132 thick, outline = figure-8 of Ø4.5 circles (8.25 × 4.5), covering the fabric opening +0.2 margin all around.
- Worksheet OEM "tub depth 2.0" was top-of-tub to bottom-of-tub, not below-flange depth — the recess is 0.75 deep and nothing on the new base extends below −0.72.
- Cup (both bores the same): base Ø2.8, taper top Ø3.5 at 3.45 up, **rim Ø4.0 at height 8.0** (measured 2026-08-30).
- **Two-tumbler reality (2026-08-30):** two Ø4.0 rims at 3.75 centers overlap by 0.25, so two of these tumblers only coexist by leaning apart within the collar clearance — true of the OEM tray too, pure seat geometry. Checks verify clearance through the collar support zone (the design's responsibility); in practice bore #2 pairs best with a can/bottle/smaller cup. If the lean annoys, a Rev B could splay the collar bores a few degrees outboard.
- Printer: **Creality CR-6 SE, 235 × 235 × 250 mm** (confirmed 2026-08-30) — generation checks enforce the envelope. Material PETG.

## Open items

- [x] Confirm printer model — Creality CR-6 SE, 235 × 235 × 250 (2026-08-30); enabled the one-piece base.
- [x] Tumbler body above the taper — rim Ø4.0 (2026-08-30); modeled as a straight flare from the taper top.
- [ ] **Hook ledge does not reconcile (raised 2026-09-14 by the measurement-model prototype).** `LEDGE = 0.50` ships in Rev G, but the worksheet's own components (plate top 11/32 + thickness 1/8) sum to 0.469, and the correction that produced 0.50 is ambiguous about whether 1/2" was to the plate's top or its underside. Consequences: 0.469 → 0.031 slack (the Rev C rattle returns); 0.500 → snug as designed; 0.625 → 0.125 interference, base may not seat. One caliper reading (upholstery top → plate underside) settles it; `SNUG_ADJUST` corrects it and only the clips reprint. **Rev G's snap fit is unverified against reconciled data until then.**
- [ ] Print + fit the coupons before the full parts: clip coupon into a real truck pocket (snap force, engagement, PETG layer survival), collar coupon into well coupon (twist feel, lug slop), cup into collar coupon (bore clearance).
- [ ] After coupons: decide whether the bayonet needs a detent bump (v1 relies on friction; lugs have ~0.025 vertical slop).
- [ ] PETG shrinkage: clearances are cut generous (0.03 plug-to-hole, ~0.1 radial cup clearance); revisit after first fit.

## Revision history

| Rev | Date | Change |
|---|---|---|
| A | 2026-08-30 | Initial design: snap-in base + two twist-lock collars (base became one piece once the CR-6 SE was confirmed). Coupons shared to the neighbor via PPBO. |
| G | 2026-09-09 | **Clip insertion path unblocked** — the leg slot stopped at the flange underside, so the only through-flange passage was the 0.134 pocket/slot overlap and the 0.189-deep hook could not enter (Brian's straight-down push snapped a clip — correct instinct, broken design). Slot now cuts through the flange (small open slot outboard of each head; doubles as drainage). New kernel check sweeps a lifted clip along its insertion path. Clip part itself unchanged. |
| F | 2026-09-04 | **Anti-tip fit** — the short coupon fooled us (cup wedged high in the loose cone and felt snug; bottomed on the well floor it had ~3/32+ radial slop, tippy — Brian). Six internal ribs whose tips follow the cup profile at `RIB_CLR` 0.015 radial (the fit knob); rib azimuths ±45°+ off the notch. Collar **+7/8 taller** (top z ≈ 4.0, Brian's headroom limit), bore goes **straight** above the cone. **Twist 25° → 35°** (~1" lug travel, Brian: more secure wrap; lugs unchanged, entries rotated). Cup-cup check threshold 0.15 → 0.10 (cups converge at the taller top — seat geometry, conscious). Fit test = ONE FULL collar print, never the short coupon again. |
| E | 2026-09-02 | **Collar wall 0.10 → 0.14** (Casey: beef it up; grows outward, cup ID untouched — Rev A coupon cup-fit result stays valid). **Scallop → deliberate U-notch** through the wall (Brian: the trim artifact looked like a print accident); notch carries all waist clearance, new kernel check proves a second collar drops in beside a locked one. Bayonet interface unchanged since Rev A — the Rev A collar coupon remains a valid twist-lock tester. |
| D | 2026-08-31 | **Snug hook engagement** — Brian measured 11/16 flange-seat-to-tip on the printed clip vs the 1/2 ledge: the 45° back-ramp let the plate corner land partway down the slope (~1/16+ vertical slack, spongy). Ramp is now shallow (~22°, `RAMP_SLOPE`) and aimed so it crosses the plate corner at exactly 0.500 below the flange seat; `SNUG_ADJUST` is the one-knob field tune. Strain limit 3.5→4.5% (in-plane, flat-printed). Rev C superseded before it was uploaded anywhere — discard those files. |
| C | 2026-08-31 | **Clips become separate flat-printed parts** (Casey's coupon snapped an integral clip at the root — layer anisotropy; T-head pockets through the flange, load-path seats the head). Collar ring top and bayonet lugs get **45° chamfers** so the upside-down collar print needs no supports (Casey). New checks: head bearing strip, installed clips kernel-clear of base/collars. |
| B | 2026-08-30 | Base footprint figure-8 → **stadium** (Brian: the recess drawing joins the circles with a rectangle; the figure-8 waist exposed the recess mid-span — cosmetic + debris trap). Flange-coverage check upgraded from bbox to kernel boolean. Clips narrowed 0.70 → 0.60 (outer corner rides the stadium's end curve; keeps snap-in strain at 3.1%). **Re-share revB coupon files on the PPBO Job** — revA copies are with the neighbor. |
