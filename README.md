# rock-wall-parts

Parametric code-CAD parts library for Rock Wall Forge & Rock Wall Manufacturing — build123d part scripts, imported cut artwork, and DXF/STEP outputs for CNC plasma, router, and 3D-print fabrication. Every job becomes a reusable, regenerable digital asset.

## Layout

```
lib/                    shared parametric helpers (panels, hole patterns, …)
projects/<job>/         one folder per job
  <job>.py              the parametric part script — the source of truth
  artwork/              source cut-art DXFs (true scale, closed curves)
  output/               generated DXF/STEP — committed as deliverable receipts
requirements.txt        build123d + ezdxf
```

## Setup (one-time)

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The venv is ~700 MB on disk (OpenCascade wheel) and gitignored.

## Workflow

1. Parametrize the part in `projects/<job>/<job>.py` — dimensions live in a PARAMETERS block at the top.
2. Artwork (decorative cutouts) is **imported, never generated**: export DXF at true scale from the design source and drop it in `artwork/`. Prefer DXF over SVG (SVG carries px/DPI unit ambiguity).
3. Run the script from its project directory with the venv active; outputs land in `output/`.
4. **Fusion import gotchas (both bitten once):** STEP — use Insert CAD into an inch design (direct Open adopts the file's mm). DXF — Insert DXF's Units dropdown defaults to document units, not the file's; set it to Inch explicitly.
5. **Verify in Fusion before CAM.** Until a script has matched a hand-built model on a real job, Fusion is the source of truth and the script is the shadow experiment.
6. Kerf compensation is CAM's job — geometry in this repo is always nominal. Current chain: generated DXF → Fusion sketch import → Fusion CAM (Brian: tools, kerf comp, post) → G-code to Jimmie's ArcDroid.
7. **Small-hole CAM recipe** (pilot circles): separate holes-only 2D Profile op with Sideways Compensation = Center, Pierce Clearance = 0, minimal lead-in. Normal compensation refuses holes below ~3/16 (and the default 0.059 pierce clearance can't fit inside them).

## Commit policy

- **Commit:** part scripts, `lib/` helpers, source artwork DXFs, output DXF/STEP (small, and they're the receipts for what was actually cut).
- **Never commit:** `.venv/`, STL/3MF meshes, renders/screenshots, Fusion `.f3d`/`.f3z` archives (all gitignored).

## Projects

- `projects/bonebrake-cover/` — 3-piece plasma-cut plumbing cover for brickwork, mountain/tree cut-in artwork (RWF client job; first shadow-experiment for this workflow).
