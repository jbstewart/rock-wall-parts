# Rock Wall Forge — Code-CAD Fabrication Pipeline

How Rock Wall Forge / Rock Wall Manufacturing (Brian Stewart's shop) designs and fabricates parts. The pipeline is: **Claude Code → build123d (Python) → STEP/DXF → Fusion 360 CAM → ArcDroid plasma**.

## Core idea

Every job is a parametric Python script, not a hand-built CAD model. The script (authored and maintained with Claude Code, using the build123d code-CAD library on the OpenCascade kernel) is the single source of truth. Running it regenerates ALL deliverables: geometry, fab drawings, and shop documents. Nothing downstream is ever hand-edited — you change the parameters and regenerate.

## Per-job structure

- Each job lives in `projects/<job>/` with a `BRIEF.md` — the spec and decision log. The brief must stay synced with every parameter change; a drifted brief is treated as a bug.
- Shared code graduates to `lib/` only when a second job needs it (materials price book, fastener data, drill-size index, drill-map generator, McMaster hardware STEPs).

## Design conventions

- **Units:** parts are authored in inches; STEP is exported in mm. Parts are built at the origin, scaled ×25.4, then placed. STEP components are labeled and colored so Fusion imports arrive named and tinted.
- **Validation:** generation-time checks gate all geometry (fit, clearances, thread engagement, rivet tail length, artwork keep-outs, spec/brief sync — 17 checks on the current job). A failed check means no files are written. Every discovered bug becomes a permanent check.
- **Artwork** (decorative cut-ins) is imported SVG/DXF, never generated or hand-drawn in Fusion; it is auto-fit and kernel-verified to clear every fastener keep-out, backing off scale automatically until it does.
- **Hardware** is McMaster-Carr catalog STEP models (no-thread versions), auto-oriented by code; the SKU embedded in the filename feeds the generated BOM. McMaster is the spec/CAD source even when parts are purchased elsewhere.

## Generated deliverables (one script run)

STEP assembly · plasma DXFs (from the same sketches as the solids, so no drift) · frame cut list · drill schedules · a to-scale drill-map PDF with lettered holes · BOM with SKUs and price-book costs · build sheet (fab print + traveler: weld requirements, drilling, finish, install) · CAM sheet (exact Fusion op settings) · program table (gcode filename, material, quantity, blank size rounded up to 1/2"). Fab prints state acceptance criteria, not technique.

## Revision control

Every job carries a `REV` letter (ASME Y14.35 style: A, B, … skipping I O Q S X Z). It is stamped into every output filename (`-revA`), every document header, the STEP assembly label, and — by hand — the Fusion-posted gcode filenames (`part-revA.gcode`). A generation check fails the build if the brief's "Current revision" line doesn't match the script. Rev bumps on any form/fit/function change. Released files are attached to the job in Playful Platypus Business Ops (the shop's business system); superseded revs are removed there, and the operator verifies the rev tag on the plasma controller's screen against the build sheet before cutting.

## CAM and plasma specifics

- Fusion import: STEP via Insert CAD into an inch design; DXF via Insert DXF with Units = Inch.
- The plasma table (ArcDroid) cuts **no finished holes**. Every hole is cut as a 1/8" pilot and drilled to final size per the generated drill schedules. Final sizes come from a fractional drill index with per-role rounding: clearance holes round UP, rivet fits stay snug, tap drills use the published fractional equivalent.
- Pilots use a dedicated small-hole recipe: a separate holes-only 2D Profile op with Sideways Compensation = Center, Lead-In/Lead-Out unchecked, Pierce Clearance = 0. Normal-compensation profiles handle the outline and artwork; kerf compensation stays in CAM, never in the geometry.

## Division of labor

Brian: design scripts, Fusion CAM, business side. Jimmie: runs the plasma table and bench work from the generated build sheet, drill map, and program table. Customer-facing workflow (quotes, deposits, questionnaires) runs in Playful Platypus Business Ops.
