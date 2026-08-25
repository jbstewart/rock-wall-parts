# Agent guidance — rock-wall-parts

Parametric code-CAD parts library for Rock Wall Forge / Rock Wall Manufacturing (Brian Stewart's shop). Read `README.md` for the workflow; each job's `projects/<job>/BRIEF.md` is that job's spec and decision log.

## How to work here

- **Never `rm` or delete files.** Propose what should be deleted and let Brian execute it. This includes "stale" outputs and files you created yourself.
- **Brian handles all git** — never commit, push, or offer to; provide commit messages when asked. **Never rewrite git history** (no rebase/amend/force-push); Brian does those personally.
- **Stay inside this repo.** Reading other repos is fine; never write outside this tree without asking Brian and getting an explicit OK first.
- **No long-running servers or watchers.** Use one-shot builds/checks (script runs, typechecks); if something genuinely needs a persistent process, ask Brian to run it.
- **Verify before declaring done**: run the script, re-import exports, check per-component labels + positions (never just the overall bbox). Don't claim something works on an unconfirmed theory — run it, or say plainly what's unverified.
- No hard-wrapped prose in docs — one line per paragraph.
- Brian: 40-year SWE (expert — skip programming 101), ~2 years CAD (explain drafting/machining vocabulary when it first appears). Jimmie (JSW) runs the plasma; Brian does CAD + Fusion CAM.

## Core conventions (violations have all bitten us — details in README)

- **Author in inches; STEP is mm.** Build parts at origin, scale ×25.4, THEN place (`place()` helper). Never `Shape.scale()` a located part — it scales about the local frame and strands the placement. `scale()` also serves as copy-on-place: placing one shape N times without copying collapses all labels to the last one.
- **Generation-time checks gate all geometry.** Every discovered bug becomes a permanent check (16 on bonebrake-cover). Never delete or weaken a check to make generation pass — fix the design, or consciously relax with a comment explaining the engineering reason.
- **Keep the BRIEF synced with every parameter change.** The brief is the spec; a drifted brief is a bug.
- **Artwork is imported, never generated.** SVG or DXF; auto-fit + kernel-verified clearance with auto-backoff. Never hand-cut art in Fusion — regeneration wipes it.
- **Plasma cuts no finished holes** — 1/8" pilots (small-hole CAM recipe: holes-only op, Sideways Comp = Center, Pierce Clearance = 0), drilled to final per generated schedules. As-built hole sizes come from a fractional drill index with per-role rounding (clearance UP; snug fits 1/64 granularity; tap = published fractional equivalent).
- **Hardware = McMaster catalog STEPs** in `lib/hardware/` ("3-D STEP no threads"; filename `<type>-<head/drive>-<thread>x<length>-<finish>-<sku>.step`); auto-oriented by `normalize_fastener()`. SKU in the filename feeds the generated BOM. Parametric primitives are the fallback.
- **Fab documents are generated, never hand-edited**: DXFs from the same sketches as the solids, cut list, drill schedules, drill map, BOM (costs from `lib/materials.py` price book), build sheet. Regenerate; don't patch outputs.
- **Fab prints state requirements, not technique** — acceptance criteria for the welder, not welding lessons.
- Fusion import gotchas: STEP → Insert CAD into an inch design; DXF → Insert DXF with Units = Inch (dialog ignores the file's declared units).
- Generalize into `lib/` only when a second job needs it (e.g., `lib/weldments.py` waits for weldment job #2).

## Commands

```sh
.venv/bin/python projects/bonebrake-cover/bonebrake_assembly.py          # real cover → output/
.venv/bin/python projects/bonebrake-cover/bonebrake_assembly.py coupon   # test coupon → output/coupon/
```

(Run from the project directory; venv setup in README.)

## Business context

RWF/RWM jobs are quoted and tracked in Playful Platypus Business Ops (tenant `rock-wall-forge`). The Bonebrake job's non-CAD workflow (site measurements, customer questionnaire, quote w/ 50% deposit) lives there — see BRIEF.md open items.
