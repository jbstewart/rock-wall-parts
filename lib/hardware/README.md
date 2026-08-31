# Catalog hardware models

Downloaded STEP models of real fasteners (McMaster-Carr → product page → CAD dropdown → 3-D STEP).
Project scripts use these automatically when a file matching the configured spec exists here,
falling back to parametric primitives otherwise. After a first download, tune the model's
rotate/z_shift config in the project script so it lands: bearing plane at origin, shank -Z.

## Filename convention

`<type>-<head/drive>-<thread>x<length>-<finish>-<sku>.step`

- thread/length use `_` for fractions: `3_8-16x1_2` = 3/8"-16 × 1/2"
- finish: `zinc`, `18-8ss`, `blackox`, `alum`, …
- sku: the vendor part number — it IS the purchase-order line; never omit it

Examples:
- `bolt-pan-phillips-3_8-16x1_2-zinc-90272A410.step`  (SKU illustrative — use the real one)
- `rivet-blind-3_16x0_25grip-alum-97447A130.step`

Scripts match on the spec prefix with a glob (e.g. `bolt-pan-phillips-3_8-16x1_2-*.step`),
so finish and SKU never require a code change — but only keep ONE file per spec prefix,
or the script will warn and pick the first alphabetically.

## Wanted by bonebrake-cover

- `bolt-pan-phillips-3_8-16x1_2-<finish>-<sku>.step` — Phillips pan head, 3/8"-16 × 1/2"
- `rivet-blind-3_16x<grip>-<finish>-<sku>.step` — 3/16" blind rivet, grip covering 0.240"
