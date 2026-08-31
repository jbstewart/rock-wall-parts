# Truck cup holder — BRIEF

Current revision: **A**

Replacement for the worn OEM dual cup holder insert in the fold-down center armrest of Brian's Silverado bench seat. 3D printed (PETG), personal part — no plasma/weld pipeline, no PPBO job. Source measurements: `MEASUREMENTS.md` (Brian, calipers, 2026-08-30) and `SilveradoCupHolder Drawing.pdf` (Brian's CAD of the foam recess).

## Problem

The OEM insert (shallow oval tray, ~1.75" bores) fails two ways: bores are too wide/shallow for the 30 oz tumblers actually used (tippy), and the four cantilever snap hooks that once retained it under the seat's embedded plastic plate have worn off flush — the insert lifts straight out.

## Architecture (DECIDED 2026-08-30)

Two-piece system, two unique printed parts (base ×1, collar ×2):

- **Base** (stays snapped into the platform): **one-piece** figure-8 plug matching the recess (the ~8.25"/211 mm flange fits the confirmed CR-6 SE bed; an earlier two-half split existed only for a feared 150 mm bed and was dropped 2026-08-30). Four fresh cantilever snap hooks engage under the embedded plate (ramped both ways → removable with a firm pull, but it normally never comes out). Each bore is a shallow well (cup floor 0.55 below flange) with a drain hole.
- **Collar** (superstructure, quantity 2, identical parts): a ~3"-tall tapered tube per cup that supports the tumbler at its full taper-top diameter (3.5"). Each collar **bayonet twist-locks** into its well — lugs drop into entry slots near the outboard end, twist ~25° toward lock. To seat a third passenger: two quarter-ish twists, lift both collars, fold the platform; the base stays put.
- Collars are one part used twice: rotating the part 180° serves the mirrored position (lugs at 135°/315° are C2-symmetric; the waist-facing scallop swaps sides correctly).

Why not clone the OEM insert: it engaged the same plate but gave no tall cup support and its bores fit nothing we own; the clips get redesigned with fresh hooks since the OEM barbs wore off flush.

Why a scallop on each collar: two 3.5" cups on 3.75" centers nearly touch — each collar is trimmed by the neighbor's envelope so collars never collide and both cups still fit simultaneously.

## Key measurements adopted (and reconciliations)

- Recess: figure-8, circle Ø3.96 (7.71 overall − 3.75 c-c, per drawing), depth 0.75. Fabric opening 7.75 × 4.
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
- [ ] Print + fit the coupons before the full parts: clip coupon into a real truck pocket (snap force, engagement, PETG layer survival), collar coupon into well coupon (twist feel, lug slop), cup into collar coupon (bore clearance).
- [ ] After coupons: decide whether the bayonet needs a detent bump (v1 relies on friction; lugs have ~0.025 vertical slop).
- [ ] PETG shrinkage: clearances are cut generous (0.03 plug-to-hole, ~0.1 radial cup clearance); revisit after first fit.

## Revision history

| Rev | Date | Change |
|---|---|---|
| A | 2026-08-30 | Initial design: two-half snap-in base + two twist-lock collars. |
