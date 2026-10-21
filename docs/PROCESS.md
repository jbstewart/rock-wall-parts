# Rock Wall Forge — Code-CAD Fabrication Pipeline

How Rock Wall Forge / Rock Wall Manufacturing (Brian Stewart's shop) designs and fabricates parts. The pipeline is: **Claude Code → build123d (Python) → STEP/DXF → Fusion 360 CAM → ArcDroid plasma**.

## Core idea

Every job is a parametric Python script, not a hand-built CAD model. The script (authored and maintained with Claude Code, using the build123d code-CAD library on the OpenCascade kernel) is the single source of truth. Running it regenerates ALL deliverables: geometry, fab drawings, and shop documents. Nothing downstream is ever hand-edited — you change the parameters and regenerate.

## Per-job structure

- Each job lives in `projects/<job>/` with a `BRIEF.md` — the spec and decision log. The brief must stay synced with every parameter change; a drifted brief is treated as a bug.
- Shared code graduates to `lib/` only when a second job needs it (materials price book, fastener data, drill-size index, drill-map generator, McMaster hardware STEPs).

## Design conventions

- **Units:** parts are authored in inches; STEP is exported in mm. Parts are built at the origin, scaled ×25.4, then placed. STEP components are labeled and colored so Fusion imports arrive named and tinted.
- **Validation:** generation-time checks gate all geometry (fit, clearances, thread engagement, rivet tail length, artwork keep-outs, spec/brief sync — 40 checks on the current job). A failed check means no files are written. Every discovered bug becomes a permanent check.
- **Artwork** (decorative cut-ins) is imported SVG/DXF, never generated or hand-drawn in Fusion; it is auto-fit and kernel-verified to clear every fastener keep-out, backing off scale automatically until it does.
- **Hardware** is McMaster-Carr catalog STEP models (no-thread versions), auto-oriented by code; the SKU embedded in the filename feeds the generated BOM. McMaster is the spec/CAD source even when parts are purchased elsewhere.

## Generated deliverables (one script run)

STEP assembly · plasma DXFs (from the same sketches as the solids, so no drift) · frame cut list · drill schedules · a to-scale drill-map PDF with lettered holes · BOM with SKUs and price-book costs · build sheet (fab print + traveler: weld requirements, drilling, finish, install) · CAM sheet (exact Fusion op settings) · program table (gcode filename, material, quantity, blank size rounded up to 1/2"). Fab prints state acceptance criteria, not technique.

## Revision control

Every job carries a `REV` letter (ASME Y14.35 style: A, B, … skipping I O Q S X Z). It is stamped into every output filename (`-revA`), every document header, the STEP assembly label, and — by hand — the Fusion-posted gcode filenames (`part-revA.gcode`). A generation check fails the build if the brief's "Current revision" line doesn't match the script. Rev bumps on any form/fit/function change. Released files are attached to the job in Playful Platypus Business Ops (the shop's business system); superseded revs are removed there, and the operator verifies the rev tag on the plasma controller's screen against the build sheet before cutting.

Superseded output files are never deleted outright. They are moved to a per-job `FOR_DELETION/` folder, which is gitignored: for anything already committed git remains the archive, and the folder is a staging area a human empties deliberately rather than a wastebasket an automated step writes to. A rev is only staged once its replacement exists and is committed, so the job is never left without a current set.

## CAM and plasma specifics

- Fusion import: STEP via Insert CAD into an inch design; DXF via Insert DXF with Units = Inch.
- The plasma table (ArcDroid) cuts **no finished holes**. Every hole is cut as a 1/8" pilot and drilled to final size per the generated drill schedules. Final sizes come from a fractional drill index with per-role rounding: clearance holes round UP, rivet fits stay snug, tap drills use the published fractional equivalent.
- Pilots use a dedicated small-hole recipe, revised 2026-10-21: a separate holes-only 2D Profile op with Sideways Compensation = Left, In computer; lead-in ON at 0.020 linear perpendicular, radius 0; Pierce Clearance = 0.020 in (0.5 mm); kerf 1.4 mm carried on the tool. This supersedes the earlier Center / leads-off / Pierce Clearance 0 recipe, which existed because the tool carried no measured kerf. 0.020 is the floor that still lets a 1/8" hole generate with lead-in on: Fusion drops any contour where lead-in plus clearance will not fit, and it does so silently, so the toolpath count gets checked against the contour count after every Generate. Standard-compensation profiles still handle the outline and artwork, and kerf compensation stays in CAM, never in the geometry. Source: `areas/fabrication/ArcDroid-Cut-Profile-Runbook.md` in pp-operations (sections 9 and 10).

## Division of labor

Brian: design scripts, Fusion CAM, business side. Jimmie: runs the plasma table and bench work from the generated build sheet, drill map, and program table. Customer-facing workflow (quotes, deposits, questionnaires) runs in Playful Platypus Business Ops.
