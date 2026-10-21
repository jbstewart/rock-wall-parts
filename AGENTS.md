# Agent guidance — rock-wall-parts

Parametric code-CAD parts library for Rock Wall Forge / Rock Wall Manufacturing (Brian Stewart's shop). Read `README.md` for the workflow; each job's `projects/<job>/BRIEF.md` is that job's spec and decision log. `docs/PROCESS.md` is the outsider-facing pipeline summary (also fed to other AI assistants) — keep it in sync when conventions here change.

## How to work here

- **Never `rm` or delete files.** Propose what should be deleted and let Brian execute it. This includes "stale" outputs and files you created yourself.
- **Superseded outputs go to `projects/<job>/FOR_DELETION/`, never to `rm`.** The folder is gitignored, so git stays the archive for anything that was committed — and anything that was NOT committed has no other copy, so say so when you stage it. Move with plain `mv`, not `git mv` (Brian stages). Sequence matters: a rev only moves out once its replacement has been generated AND committed, or the job is briefly left with no current files. Propose the move and let Brian call it; `FOR_DELETION/` itself is emptied by Brian, never by an agent. `output/` holds only the current rev — there is no permanent archive folder, git is that. One exception stays put: outputs for something physically fabricated (an already-cut coupon) are receipts for a part that exists, so they are current, not stale.
- **Brian handles all git** — never commit, push, or offer to; provide commit messages when asked. **Never rewrite git history** (no rebase/amend/force-push); Brian does those personally.
- **Stay inside this repo.** Reading other repos is fine; never write outside this tree without asking Brian and getting an explicit OK first.
- **No long-running servers or watchers.** Use one-shot builds/checks (script runs, typechecks); if something genuinely needs a persistent process, ask Brian to run it.
- **Verify before declaring done**: run the script, re-import exports, check per-component labels + positions (never just the overall bbox). Don't claim something works on an unconfirmed theory — run it, or say plainly what's unverified.
- No hard-wrapped prose in docs — one line per paragraph.
- Brian: 40-year SWE (expert — skip programming 101), ~2 years CAD (explain drafting/machining vocabulary when it first appears). Jimmie (JSW) runs the plasma; Brian does CAD + Fusion CAM.

## Core conventions (violations have all bitten us — details in README)

- **Author in inches; STEP is mm.** Build parts at origin, scale ×25.4, THEN place (`place()` helper). Never `Shape.scale()` a located part — it scales about the local frame and strands the placement. `scale()` also serves as copy-on-place: placing one shape N times without copying collapses all labels to the last one.
- **Generation-time checks gate all geometry.** Every discovered bug becomes a permanent check (40 on bonebrake-cover). Never delete or weaken a check to make generation pass — fix the design, or consciously relax with a comment explaining the engineering reason.
- **Keep the BRIEF synced with every parameter change.** The brief is the spec; a drifted brief is a bug.
- **Every job carries a `REV` letter** (ASME Y14.35 letters — skip I O Q S X Z, then AA, AB…), stamped into every output filename (`-revA`) and document header, matched by the BRIEF's "Current revision" line (generation check) and its revision-history table. Bump on any form/fit/function change; gcode posted from Fusion is named to match. Released files live as attachments on the PPBO Job — superseded revs are removed there when a new rev is attached.
- **Artwork is imported, never generated.** SVG or DXF; auto-fit + kernel-verified clearance with auto-backoff. Never hand-cut art in Fusion — regeneration wipes it.
- **Plasma cuts no finished holes** — 1/8" pilots (small-hole CAM recipe, revised 2026-10-21: holes-only op, Sideways Comp = **Left, In computer**, lead-in **ON at 0.020 linear perpendicular**, Pierce Clearance **0.020 in (0.5 mm)**, kerf **1.4 mm** on the tool — supersedes the old Center / leads-off / clearance-0 recipe; source is `areas/fabrication/ArcDroid-Cut-Profile-Runbook.md` in pp-operations, and per-job settings live in the generated CAM sheet), drilled to final per generated schedules. As-built hole sizes come from a fractional drill index with per-role rounding (clearance UP; snug fits 1/64 granularity; tap = published fractional equivalent).
- **Hardware = McMaster catalog STEPs** in `lib/hardware/` ("3-D STEP no threads"; filename `<type>-<head/drive>-<thread>x<length>-<finish>-<sku>.step`); auto-oriented by `normalize_fastener()`. SKU in the filename feeds the generated BOM. Parametric primitives are the fallback.
- **Fab documents are generated, never hand-edited**: DXFs from the same sketches as the solids, cut list, drill schedules, drill map, BOM (costs from `lib/materials.py` price book), build sheet. Regenerate; don't patch outputs.
- **Fab prints state requirements, not technique** — acceptance criteria for the welder, not welding lessons.
- Fusion import gotchas: STEP → Insert CAD into an inch design; DXF → Insert DXF with Units = Inch (dialog ignores the file's declared units).
- Generalize into `lib/` only when a second job needs it (e.g., `lib/weldments.py` waits for weldment job #2).

## Commands

```sh
.venv/bin/python projects/bonebrake-cover/bonebrake_assembly.py          # real cover → output/
.venv/bin/python projects/bonebrake-cover/bonebrake_assembly.py coupon   # test coupon → output/coupon/
.venv/bin/python projects/arcdroid-coupons/arcdroid_coupons.py           # ArcDroid profile + X2 coupons → output/
```

(Run from the project directory; venv setup in README.)

## Business context

RWF/RWM jobs are quoted and tracked in Playful Platypus Business Ops (tenant `rock-wall-forge`). The Bonebrake job's non-CAD workflow (site measurements, customer questionnaire, quote w/ 50% deposit) lives there — see BRIEF.md open items.
