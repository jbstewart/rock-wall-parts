"""Bonebrake plumbing cover — plasma-cut panel with cut-in artwork.

CURRENT CONFIG: 2.5" x 6.25" single test piece (pattern/system shakedown).

Workflow notes:
- Panel geometry (outline, mounting holes) is parametric build123d code.
- Artwork is IMPORTED, never generated. For plasma the deliverable is 2D cut
  curves, so the artwork entities are scaled/placed and merged into the panel
  DXF directly (no 3D boolean needed) — CAM treats each closed loop as a cut.
- Frame/border entities in the artwork DXF (LINE/LWPOLYLINE rectangles from
  the design export) are filtered out; only the art curves survive.
- Fit is validated: the art's bounding box must land inside the panel with
  the configured margin, clear of the mounting-hole band.
- Kerf compensation is CAM's job — geometry here is nominal.

Run:  ../../.venv/bin/python bonebrake_cover.py   (from this directory)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import ezdxf  # noqa: E402
from ezdxf.math import Matrix44  # noqa: E402

from build123d import Unit  # noqa: E402
from build123d.exporters import ExportDXF  # noqa: E402

from lib.panels import edge_hole_positions, holes_at, panel_outline  # noqa: E402

# --------------------------------------------------------------- PARAMETERS
# All inches.
PANEL_WIDTH = 2.5
PANEL_HEIGHT = 6.25
CORNER_RADIUS = 0.125
MATERIAL_NOTE = "test coupon — gauge TBD"

HOLE_DIAMETER = 0.201
HOLE_EDGE_INSET = 0.4
HOLE_ROWS = 2

ARTWORK_FILE = Path(__file__).parent / "artwork" / "ArtLayer.dxf"
ARTWORK_EXCLUDE_TYPES = {"LINE", "LWPOLYLINE"}  # export frames, not art
ARTWORK_MARGIN = 0.25  # min gap between art bbox and panel edge

OUTPUT = Path(__file__).parent / "output" / "bonebrake-test.dxf"

# --------------------------------------------------------------- BUILD


def corner_hole_positions() -> list[tuple[float, float]]:
    """Mounting pairs at top and bottom (matches the install photo), inset from edges."""
    x = PANEL_WIDTH / 2 - HOLE_EDGE_INSET
    y = PANEL_HEIGHT / 2 - HOLE_EDGE_INSET
    return [(-x, y), (x, y), (-x, -y), (x, -y)]


def build_panel_dxf(path: Path) -> None:
    """Panel outline + mounting holes via build123d, exported to DXF."""
    panel = panel_outline(PANEL_WIDTH, PANEL_HEIGHT, CORNER_RADIUS)
    panel -= holes_at(corner_hole_positions(), HOLE_DIAMETER)
    exporter = ExportDXF(unit=Unit.IN)
    exporter.add_shape(panel)
    exporter.write(str(path))


def art_entities(doc):
    return [e for e in doc.modelspace() if e.dxftype() not in ARTWORK_EXCLUDE_TYPES]


def art_bbox(entities):
    """Conservative bbox from spline control points / entity points."""
    xs, ys = [], []
    for e in entities:
        if e.dxftype() == "SPLINE":
            for p in e.control_points:
                xs.append(p[0])
                ys.append(p[1])
        elif e.dxftype() in ("ARC", "CIRCLE"):
            xs += [e.dxf.center.x - e.dxf.radius, e.dxf.center.x + e.dxf.radius]
            ys += [e.dxf.center.y - e.dxf.radius, e.dxf.center.y + e.dxf.radius]
    return min(xs), min(ys), max(xs), max(ys)


def merge_artwork(panel_dxf: Path) -> None:
    """Scale/center the artwork curves onto the panel and append to its DXF."""
    art_doc = ezdxf.readfile(str(ARTWORK_FILE))
    entities = art_entities(art_doc)
    x0, y0, x1, y1 = art_bbox(entities)
    art_w, art_h = x1 - x0, y1 - y0

    # Full panel width available (holes live at top/bottom); vertically the art
    # must clear the hole rows plus margin.
    hole_band = HOLE_EDGE_INSET + HOLE_DIAMETER / 2 + ARTWORK_MARGIN
    avail_w = PANEL_WIDTH - 2 * ARTWORK_MARGIN
    avail_h = PANEL_HEIGHT - 2 * hole_band
    scale = min(avail_w / art_w, avail_h / art_h)

    # center art bbox on panel origin (panel is centered on origin)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    m = (
        Matrix44.translate(-cx, -cy, 0)
        @ Matrix44.scale(scale, scale, 1)
    )

    out_doc = ezdxf.readfile(str(panel_dxf))
    msp = out_doc.modelspace()
    for e in entities:
        clone = e.copy()
        clone.transform(m)
        msp.add_entity(clone)
    out_doc.saveas(str(panel_dxf))

    print(
        f"artwork: {len(entities)} curves, {art_w:.3f} x {art_h:.3f} source, "
        f"scale {scale:.4f} -> {art_w * scale:.3f} x {art_h * scale:.3f} placed"
    )


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    build_panel_dxf(OUTPUT)
    merge_artwork(OUTPUT)
    print(f'wrote {OUTPUT}  ({PANEL_WIDTH}" x {PANEL_HEIGHT}", {MATERIAL_NOTE})')


if __name__ == "__main__":
    main()
