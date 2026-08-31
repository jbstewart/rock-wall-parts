"""Shared helpers for Rock Wall panel-style parts (plasma 2.5D workflow).

Conventions:
- All dimensions in inches unless a function says otherwise.
- Sketches are built on the XY plane; a "panel" is a filleted rectangle with
  optional hole features, exported as a flat DXF profile for CAM.
- Kerf compensation is CAM's job (Fusion CAM in the current chain) — never offset geometry here.
"""

from build123d import (
    BuildSketch,
    BuildLine,
    Circle,
    Location,
    Locations,
    Rectangle,
    RectangleRounded,
    Sketch,
)


def panel_outline(width: float, height: float, corner_radius: float = 0.0) -> Sketch:
    """Rectangular panel outline centered on the origin, optional rounded corners."""
    with BuildSketch() as sk:
        if corner_radius > 0:
            RectangleRounded(width, height, corner_radius)
        else:
            Rectangle(width, height)
    return sk.sketch


def edge_hole_positions(
    width: float,
    height: float,
    inset: float,
    rows: int,
) -> list[tuple[float, float]]:
    """Mounting-hole centers: `rows` evenly spaced pairs down the two side edges.

    Row 1 is at the top, row `rows` at the bottom, all inset from the edges.
    Returns (x, y) tuples centered on the panel origin.
    """
    xs = (-(width / 2 - inset), width / 2 - inset)
    if rows == 1:
        ys = [0.0]
    else:
        span = height - 2 * inset
        ys = [height / 2 - inset - i * span / (rows - 1) for i in range(rows)]
    return [(x, y) for y in ys for x in xs]


def holes_at(positions: list[tuple[float, float]], diameter: float) -> Sketch:
    """A sketch of circles (to subtract from a panel) at the given centers."""
    with BuildSketch() as sk:
        with Locations(*[Location((x, y)) for x, y in positions]):
            Circle(diameter / 2)
    return sk.sketch
