# Bonebrake Cover — Assembly Brief

Spec for `bonebrake_assembly.py` (dual-config: default = real cover, `coupon` arg = test coupon → `output/coupon/`, self-named files). All inches. Current as of 2026-10-11.

Current revision: **D** — the script's `REV` must match this line (generation check); every output filename carries `revD`, and Fusion-posted gcode must be named to match. Bump on any form/fit/function change (dimensions, holes, patterns, material, finish, artwork); letters skip I O Q S X Z per ASME Y14.35. On release: attach new-rev files to the PPBO Job and remove the superseded ones. History at bottom.

> ## Artwork cut density — cleared 2026-10-15, with one judgement call open
>
> Brian flagged plasma cuts "within 1/8" on the face. Two gating checks now measure it. **Both pass on `ArtLayer-Final-Rev-02.svg`.** The panel is cuttable; what follows is why, and the one number still resting on judgement.
>
> **The first version of these checks was wrong and is worth recording.** It compared pairs of points on the cut contours and reported the smallest gap. That is meaningless for a *tapered point* of steel: its width goes to zero at the tip by definition, so the "minimum" it reports is an artefact of how far back from the tip the sampling filter happens to land. It reported the artwork edit of 2026-10-15 as a 24% regression (0.0735 → 0.0602) when the edit was in fact a **7.5% improvement**. Brian disbelieved the result, which is the only reason it was caught.
>
> **What replaced it:** rasterise at 0.005, erode by floor/2, and look at what the erosion removed. Stable under reshaping, and it separates the two things the old metric conflated — a tapered tip that thins out (cosmetic; plasma cannot hold a knife edge) from a long parallel-sided ribbon (the scrap risk, because a ribbon has no adjacent metal to sink the arc heat). So the gate is on the **length of a too-thin run**, not on a minimum width.
>
> | | floor | longest run | gate |
> |---|---|---|---|
> | steel between cuts | 0.1196 (1× t, 11ga actual) | **0.252** | 0.957 |
> | cut-away art | 0.110 (2× kerf) | **0.133** | 0.957 |
>
> 0.32 in² of steel is thinner than the floor (0.11% of the panel) in 20 ribbons, and 0.17 in² of art (0.24%) in 12. All of it is short tapers; nothing approaches a ribbon.
>
> - **`MAX_THIN_RUN = 8 × thickness = 0.957" is the judgement call.** The floors are process limits; this one is reasoning — below roughly that length, surrounding metal sinks the heat. The current worst run clears it 3.8×, so there is real margin, but the number has not been proven on steel. A 4 × 4 coupon of the densest band (y −12.0 … −9.5, which holds 11 of the 20 ribbons) settles it before a 41" blank is committed.
> - **Cut ordering in the dense band** is the one process lever available on this job: run adjacent contours non-consecutively so each thin feature cools before its neighbour is cut. Split the profile op or reorder it rather than letting Fusion choose.
> - **The `revC` files in `output/` are stale** — generated from the superseded artwork, uncommitted, never released. An artwork change is a form/fit/function change, so the next generation must **bump `REV` to D first, then run**. Running before the bump overwrites outputs under the wrong rev letter; that has already happened once on this job.
> - Locations are reported as **(u, v) normalised to the artwork bounding box, origin lower left** — an SVG carries no dimensions, so (u, v) is the only coordinate that survives the round trip into a drawing program.
> - `webmap.py` is the iteration loop: edit the SVG, run it, see what moved. It imports the same `thin_features()` the gate uses, so the map cannot disagree with the checks.

## Site (Michelle Bonebrake, 887 W 330 S, Logan — indoor brick wall)

Jagged pipe channel floor-to-cap. The top cap course OVERHANGS: the cover top must tuck under the lip. Side bars carry ALL brick bearing (top/bottom bars bridge the channel).

**Site visit 2026-10-11 (Brian) — every Rev A/B hedge is now a measurement.** The leak repair tore brick out for pipe access and the carpet was replaced afterwards, leaving a bare strip of concrete along the wall that the cover has to cover. Measured:

| | Value | Drives |
|---|---|---|
| Widest brick gap anywhere | **5.5"** (was an estimate) | `OPENING_W`, bar bearing |
| Brick gap where it meets the floor | **4.25"** — 2.00 / 2.25 of bare strip either side | `BOTTOM_GAP_MARGINS` |
| Concrete floor → underside of cap | **41-11/16" (41.6875)** | `UNDER_CAP_H` |
| Bare concrete strip | **8.5" along the wall × 1.5" into the room** | `BARE_L`/`BARE_D` → base AND cover width |
| New carpet + pad height | **1.25"** | base finishes 0.75 below the pile |

Consequences, all Rev C: the cover grew a **floor base** to fill the bare strip; cover width is no longer free (**W 9 → 8.5**, matching the base and the strip); the base eats into the floor-to-cap height so every vertical component shortened (**H 41.25 → 41.125**, giving 0.5 + 41.125 = **41.625 finished** with 1/16 of gap under the cap). "Carpet hides shortfall at the floor" is retired as an install story — the unit stands on its own base and the slack is at the TOP.

## Configurations

| | Real cover | Coupon (texture/demo) |
|---|---|---|
| W × H | **8.5 × 41.125** (measured 2026-10-11) | 2.5 × 6.25 |
| Bar | 1.5 | 0.5 |
| Art | `artwork/*final*` (SVG or DXF; ArtLayer.dxf = loud placeholder) | ArtLayer.dxf (single tree) |
| Rivets | **6** (3 pairs) — see the station grid below | 4 (2 pairs) |
| Bolts | **8** (4 pairs) | 4 (corners) |
| Panels cut | 1 face + 1 middle | 1 face + **2 middles** (one per candidate gray texture for Michelle's pick) |

## Datums / stackup (brick → out)

Origin = center of frame back face; +Z out of brick. Frame 0.25×BAR flat bar, mitered + welded, outer corners radiused → z [0, 0.25]. Middle 11ga (nominal 1/8) gray → [0.25, 0.375]. Face 11ga black, art cut through → [0.375, 0.50].

## Base (Rev C — new)

Two pieces of 1/4 × 1-1/2 flat bar, **8.5" long**, laid flat one on the other and **plug-welded** through the LOWER bar (3× 9/16" holes on its centreline at x 0, ±3.5 — 9/16 is the AWS D1.1 plug minimum for 1/4 plate, `t + 5/16`). Welds ground flush to the BOTTOM face so the base doesn't rock on concrete; the UPPER bar's top face is left clean because **both the frame and the panel unit seat on it**. That is why the holes go in the bottom bar, not the top.

Finished base 8.5 L × 1.5 deep × 0.5 tall, occupying y [−H/2−0.5, −H/2], z [0, 1.5] — back edge flush with the frame's back face, so 1.0" projects forward of the finished cover face. Top front edge and both top ends get a ~1/8" round-over (Brian promised a toe break; the base finishes 0.75" below the 1.25" carpet anyway, so this is belt-and-braces).

**Welded to the frame** — the frame's bottom bar stands on the base, fillet-welded along the full 8.5" front seam. Welding rather than leaving it loose is what guarantees the base top and the frame bottom are coplanar: the panel unit's bottom edge lands on that surface, and a loose base sitting a hair proud or low would show a step or a gap at the floor line. The cost is install (see below).

## Hardware & joints (as-built sizes = fractional drill index, per-role rounding)

- **Frame → brick (REWORKED Rev C):** 6× Tapcon 1/4" × 1-1/4" flat Phillips, **positions now designed and drilled in the shop** (through Rev B they were installer's choice, on site, and absent from fab outputs). Brian located them against the actual brick on 2026-10-11: on the side-bar centreline (3/4 from the outer edge → x ±3.5), at **5, 20 and 40 inches above the concrete floor** = 4.5 / 19.5 / 39.5 above the frame's bottom edge. Frame: **9/32 through + 82° countersink to 0.500 dia, cut from the BACK face**, 0.126 deep, leaving 0.124 of bar. Brian asked for 1/4" holes; 1/4 will not pass a 1/4 Tapcon's 0.250 thread crest (the screw threads the BRICK, not our steel), so clearance rounds up per house rule — generation check. On site now: 3/16 carbide SDS only.
  - Anchor edge distance is the thin spot: at W=8.5 the anchors sit only **0.75" outboard of the widest part of the gap** (W=9 gave 1.25"). Brian confirmed brick meat on site; the install sheet says to verify sound brick at each of the six before drilling and to relocate along the bar if one is crumbly.
- **Face+middle (riveted unit):** 3/16 × 1/2 aluminum SOLID brazier rivets (McMaster 97484A245 / Amazon on hand; 3/8-length fails tail check at 0.67d). Bucked on the bench — factory heads on face, shop heads (~0.281 × 0.094) nest in frame reliefs. Panel holes **13/64** (snug; shank swells). Tail = 1.33d ✓.
- **Unit → frame:** 8× **5/16-18 × 1/2** flanged button-head hex (Rev B — sourced locally 2026-08-30; Brian judged 5/16 heads better proportioned than the original 1/4-20 91355A081. **VERIFY purchased length is 1/2** — longer fails the brick-protrusion check). Panels: **11/32** clearance (rounds UP, +0.031 over major). Frame corners: tap drill **17/64** → tapped 5/16-18, 4.5 threads. Flush at nominal 0.500 stack. Purchased length **verified 1/2, black oxide** (2026-08-30). Catalog STEP in lib/hardware/ (91255A578 equivalent; dimensions kernel-verified: head Ø0.546, OAL 0.666).
- Frame rivet reliefs: **11/32** (shop heads clear + hide inside bar) — same bit as the bolt clearance (A + D share, Rev B).
- **Fastener station grid (Rev C):** one uniform pitch down each side bar — **7 stations**, corner to corner, 6.604" apart. `BOLTS_PER_SIDE` of them are bolts (always including both corners) and the rest are rivets, so the visible rhythm of dots down the edge is identical whichever way the count lands; only which ones are bolt heads changes. Shipping **4 bolts + 3 rivets per side** (8 bolts, 6 rivets): Brian's 6-vs-8 question was about the panel edge standing off the frame mid-span, and 4 corners alone left a 39.6" unsupported run. 4/side gives a 13.21" bolt pitch; 3/side would give 19.81". `MAX_BOLT_PITCH = 15.0` is a generation check that encodes this decision — switching to `BOLTS_PER_SIDE = 3` trips it on purpose, so raise the limit *with a note* rather than deleting it.
- **Fastener edge inset (Rev B, coupon lesson):** every rivet and corner-bolt center sits **≥ 3/4"** from the panel edges — the coupon's BAR/2 inset (0.25) left no room to drill the frame relief holes. Generation check; coupon config exempt (already cut).

## Finish (DECIDED)

Hammered black on face + frame (forge texture, hides mill scale; powder coat $100 = too rich). Middle: light gray field, **texture via Michelle's Customer Questionnaire** — options photographed on the coupon (engine-turned + clear vs gray stone-texture can); texture scale must stay fine (shows only through cutout slivers). Middle EDGES black. Rivet finish (bright vs blacked) = questionnaire Q2. Paint after drill/tap, before riveting; mask tapped holes.

## Plasma / CAM

Panel DXF holes are **1/8" PILOTS** (drilled to final per schedules; clamp face+middle, drill pairs together). Pilots cut via the **small-hole CAM recipe** (settings finalized 2026-08-25): separate holes-only 2D Profile op, Passes→Sideways Comp = CENTER, Linking tab: Leads→Lead-In (Entry) + Lead-Out (Exit) both UNCHECKED, Piercing→Pierce Clearance = 0 (normal comp refuses < ~3/16; default 0.059 pierce clearance can't fit). Art + outline = normal op. Kerf stays in CAM. Full per-op setup is the generated **CAM sheet** (`…-camsheet-revX.md`) — set up Fusion from it, not from memory.

## Validation (37 checks gate generation)

Window exists ×2 · side bars land fully on brick when centred · side bar keeps ≥1.0 bearing at 0.25 off-centre · cover + base clears the cap lip · top gap ≥ 1/16 · assembly can be tilted in under the cap (max diagonal) · base fills the bare strip · base finishes below the carpet · side bars find brick at the floor gap · plug holes meet AWS D1.1 minimum · plug holes leave metal all round · rivet tail 1.3–1.7d · shop head hides in frame · shop head clears relief · rivet holes land on bar · fastener centers ≥ 3/4 from edges (Rev B) · bolt not into brick · ≥2 threads engaged · corner holes on bar · rivet snug fit (0 < slop ≤ 0.02) · bolt clearance clears major · pilot ≥ 2× kerf (center-comp recipe) · pilot ≤ smallest finish − 0.01 · artwork clears every fastener keep-out (kernel boolean, auto-backoff fit) · Tapcon hole clears thread crest · Tapcon countersink leaves bar under the head · Tapcon heads finish flush · Tapcon holes wholly on the side bars · Tapcon countersinks clear every other frame hole · Tapcon anchors clear of the gap · bolt pitch ≤ MAX_BOLT_PITCH · every station is a bolt or a rivet, never both · BRIEF current revision matches script `REV` · **exactly one artwork 'final' candidate** · **plasma webs ≥ 1× material thickness** · **cut-away slivers ≥ 2× kerf**.

**The two cut-density checks (added 2026-10-15)** are the only ones here that a parameter change cannot satisfy — they measure the *artwork*, which is an imported file. `MIN_WEB` (1× thickness) and `MIN_SLIVER` (2× kerf) are process limits of the ArcDroid on 11ga and are not relaxation candidates. `MAX_THIN_RUN` is engineering judgement (8× thickness) and is the number a coupon should confirm; raise it only with a coupon result behind it, never to get a build out. Measurement is by rasterised erosion, not contour-pair sampling — see the note at `RASTER_PITCH` for the taper problem that forced the rewrite. Adds ~10 s to a run.

**Consciously relaxed at Rev C:** "side bars bear on brick past the jag" demanded a further 0.25" of bar beyond the widest jag. That margin hedged an *estimated* opening; the opening is now measured at 5.5 max and the cover width is no longer free (it is set by the bare strip). The check became "fully on brick when centred" (2.750 ≥ 2.750, exactly), and the hedge was re-expressed as the physical thing it stood in for: **1.25" of the 1.5" bar still on brick with the cover 0.25" off centre**. Not deleted — replaced with something truer.

## Outputs (one command per config)

STEP assembly (named + colored; Insert CAD into inch design) · face/middle DXFs from the same sketches (Unit.IN; Insert DXF w/ Units=Inch) · frame cut list (miter long-points) + drill schedule · panel drill schedule · drill-map PDF (lettered holes, fractional legend; PDF so it attaches to the PPBO Job as a document, not an image) · BOM (SKUs from lib/hardware filenames; material $ from lib/materials.py price book) · build sheet (fab print + traveler + finish + install §) · CAM sheet (Fusion op settings incl. small-hole recipe) · program table (gcode name / material / qty / blank W×H rounded UP to 1/2", in both CAM + build sheets) · check report · base cut list + plug-weld schedule (Rev C) · customer render (`render_assembly.py` → PNG, gitignored presentation aid, NOT a fab document — layered paint order, not depth-sorted).

## Open items

1. **Confirm `MAX_THIN_RUN` on steel, then release Rev D.** Both cut-density checks pass on `ArtLayer-Final-Rev-02.svg` (longest steel run 0.252 against a 0.957 gate, longest art run 0.133), but the gate itself is engineering judgement — 8 × material thickness, reasoned from heat sinking, never proven on this machine. Cut the artwork coupon described below before committing a 41" blank; it also fixes the real limit so the gate stops being a guess. Then release **Rev D**: bump `REV` first (an artwork change is form/fit/function, and running before the bump overwrites outputs under the wrong letter — that has already happened once here), add the history row, regenerate, re-attach on the PPBO Job and remove the revB and revC attachments.
   **Coupon design:** one blank, 8.5 × 11 of the same 11ga, three zones on one uncut piece so overall flatness can be checked across it. **Zone A**, y −13.4…−9.4 of the real art: the densest band, 11 of the 20 steel ribbons, the worst run (0.252) and the thinnest steel (0.0707), plus the y −13.208 pilot row. **Zone B**, y +4.5…+6.5: the worst art ribbon (0.133 run, 0.0922 wide), which is nowhere near Zone A. **Zone C**, a calibration ladder of parallel-sided webs at 0.040 / 0.060 / 0.080 / 0.100 / 0.120 / 0.160 wide × 0.25 / 0.5 / 1.0 / 2.0 long, bracketing the real art's 0.0707–0.1118 thickness and 0.059–0.252 runs — the 1.0 and 2.0 rows are what actually test the gate. Cut it from the same CAM setup, same consumables at the same wear state, same ordering and same back-to-back timing as the real panel: a coupon cut leisurely tells you nothing about a panel cut continuously. Acceptance: survival per ladder cell, flatness across the whole coupon by straightedge and feeler (this is the one that scales — what kills the assembly is the face not seating), local curl at each surviving feature, dross, and detail loss against the DXF. It cannot predict cumulative bow over 41"; that risk is managed by cut ordering.
2. ~~Site tape visit~~ — **done 2026-10-11**, all dimensions above.
3. Michelle questionnaire: backer texture, rivet finish.
4. Quote via PPBO after answers — 50% deposit, balance on install, ACH-preferred. Rev C adds material (2 base bars, 4 more bolts, 2 more Tapcons) and shop labour (6 countersinks + 3 plug welds now in the shop, not on site).
5. **Install has 1/16" of head room and the unit is one weldment.** It cannot be swung in like a picture frame — max diagonal is 41.652 vs 41.6875 available. It goes in plumb, lifted just clear of the floor, slid straight back. Dry-fit before drilling brick. If that turns out to be unworkable in the room, the fallback is to NOT weld the base to the frame and set it as a separate plinth — at the cost of a possible step at the floor line.
6. Floor-to-cap was measured at one place. The base is 8.5" long; if the concrete falls away across that span the base rocks or the top binds. Bed on adhesive, never shim up.

## Revision history

Release commit = the commit that adds this rev's outputs (and removes the superseded ones); fill the hash in right after committing — it makes "show me the exact Rev X drill map" a `git show <hash>:<path>` one-liner.

| Rev | Date | Release commit | Change |
|---|---|---|---|
| A | 2026-08-25 | ce1c499 | Initial release under revision control (design state as specified above: 9 × 41.25 provisional, 10 rivets, hammered black / gray texture TBD). |
| D | 2026-10-15 | _fill on commit_ | **Artwork cut density.** Brian flagged plasma cuts "within 1/8" on the face; two checks now gate it (`MIN_WEB` = 1× material thickness, `MIN_SLIVER` = 2× kerf, gated on the LENGTH of a too-thin run via `MAX_THIN_RUN`). Artwork replaced with `ArtLayer-Final-Rev-02.svg` — 7.5% less too-thin steel, 23 → 20 ribbons. Both checks pass (longest steel run 0.252, longest art run 0.133, gate 0.957). Also: a check that exactly one `*final*` artwork candidate exists, after a rename exposed that the auto-pick is alphabetical, not newest. **The first version of the cut-density metric was wrong** — contour-pair minimum gap, which is meaningless on a taper — and reported a 24% regression on an edit that was a 7.5% improvement; replaced with rasterised erosion. Artwork coupon added (`cutcoupon.py`) to prove `MAX_THIN_RUN` on steel. Geometry otherwise identical to Rev C. |
| C | 2026-10-11 | _fill on commit_ | **Site visit — measured, plus a floor base.** Carpet was replaced after the leak repair and the brick removed for pipe access left a bare strip of concrete (8.5 × 1.5) along the wall. Added a **base**: two 1/4 × 1-1/2 bars, 8.5 long, plug-welded (3× 9/16 in the lower bar), welded under the frame, exposed top arrises rounded. **W 9 → 8.5** (matches base + strip), **H 41.25 → 41.125** (base 0.5 + 41.125 = 41.625 under a measured 41.6875 cap). `OPENING_W` 5.5 confirmed by tape. **Frame→brick anchors become designed geometry**: 6× Tapcon at 5/20/40 off the concrete on the bar centreline, 9/32 + 82° countersink cut in the SHOP (Brian asked for 1/4" holes — they won't pass a 1/4 Tapcon's thread crest; new check). **Fastener station grid**: 7 uniform stations per side, 8 bolts + 6 rivets (was 4 bolts + 10 rivets) — answers Brian's 6-vs-8 by cutting the bolt pitch from 39.6" to 13.2". 16 new checks. |
| B | 2026-08-30 | _fill on commit_ | Corner bolts 1/4-20 → **5/16-18 × 1/2** (sourced locally; better head proportion): clearance 9/32 → 11/32 (now shares the relief bit), tap 13/64 → 17/64. Fastener edge inset locked at **3/4"** with a new check (coupon revealed reliefs undrillable at BAR/2 inset). Real-cover geometry otherwise unchanged (inset was already 0.75 by coincidence of BAR=1.5). |
