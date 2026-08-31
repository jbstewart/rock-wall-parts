"""Shop drill-map generator — a to-scale one-page PDF for the drill press.

For 2.5D panel/frame parts the 'drawing' is just the outline plus holes, so
this renders each part to scale with crosshaired holes, per-hole reference
letters, and a legend table of drill callouts. Regenerated with every run,
it can never drift from the DXFs. PDF (not SVG) because the map is attached
to the PPBO Job as a document — image formats read as the wrong kind of file.

API:
    drill_map(parts, out_path, title, note=None)
      parts: list of dicts:
        name       str
        width      float (in)
        height     float (in)
        corner_r   float (in)
        holes      list of (x, y, ref) — positions in part coords (origin center)
        window     optional (w, h) — inner cutout (frames)
      refs: dict ref-letter -> description string (legend rows)
"""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

PX = 60          # points per inch of part (page is sized to content, print scales to fit)
MARGIN = 40      # sheet margin pt
GAP = 50         # gap between part views pt
CROSS = 8        # crosshair overhang pt

INK = HexColor("#111111")
DIM = HexColor("#444444")


def drill_map(parts, refs, out_path, title, note=None):
    views = []
    x_cursor = MARGIN
    max_h = 0.0
    for part in parts:
        pw, ph = part["width"] * PX, part["height"] * PX
        views.append((part, x_cursor, pw, ph))
        x_cursor += pw + GAP
        max_h = max(max_h, ph)

    legend_y = MARGIN + 30 + max_h + 40
    legend_h = 22 * (len(refs) + 1) + 10
    # Page must fit the text too, not just the part views — on small parts
    # (coupon) the legend/note are wider than the geometry.
    text_w = max(
        [stringWidth(title, "Helvetica-Bold", 16)]
        + [24 + stringWidth(d, "Helvetica", 12) for d in refs.values()]
        + ([stringWidth(note, "Helvetica", 11)] if note else [])
    )
    width = max(x_cursor - GAP, MARGIN + text_w) + MARGIN
    note_h = 40 if note else 10
    height = legend_y + legend_h + note_h + MARGIN

    c = Canvas(str(out_path), pagesize=(width, height))
    c.setTitle(title)
    c.setStrokeColor(INK)
    c.setFillColor(INK)

    # Layout math above is top-down (y grows downward, like the old SVG);
    # PDF's origin is bottom-left, so every y flips through the page height.
    def Y(y: float) -> float:
        return height - y

    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN, Y(MARGIN - 12), title)

    for part, vx, pw, ph in views:
        top = MARGIN + 30
        cx, cy = vx + pw / 2, top + ph / 2
        c.setLineWidth(1.5)
        c.roundRect(vx, Y(top + ph), pw, ph, part["corner_r"] * PX)
        if part.get("window"):
            ww, wh = part["window"][0] * PX, part["window"][1] * PX
            c.rect(cx - ww / 2, Y(cy + wh / 2), ww, wh)
        for hx, hy, ref in part["holes"]:
            px, py = cx + hx * PX, cy - hy * PX  # layout y is down
            r = 5
            c.setLineWidth(1.0)
            c.circle(px, Y(py), r)
            c.setLineWidth(0.75)
            c.line(px - r - CROSS, Y(py), px + r + CROSS, Y(py))
            c.line(px, Y(py - r - CROSS), px, Y(py + r + CROSS))
            c.setFont("Helvetica-Bold", 11)
            c.drawString(px + r + 3, Y(py - r - 3), ref)
        c.setFont("Helvetica", 12)
        c.drawCentredString(cx, Y(top + ph + 18),
                            f'{part["name"]} — {part["width"]:.3f}" × {part["height"]:.3f}"')

    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, Y(legend_y), "Drill legend")
    y = legend_y + 20
    for ref, desc in refs.items():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(MARGIN, Y(y), ref)
        c.setFont("Helvetica", 12)
        c.drawString(MARGIN + 24, Y(y), desc)
        y += 22
    if note:
        c.setFont("Helvetica", 11)
        c.setFillColor(DIM)
        c.drawString(MARGIN, Y(y + 12), note)

    c.showPage()
    c.save()
    return Path(out_path)
