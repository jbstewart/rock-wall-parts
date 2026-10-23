"""Generate the button icons for the Check & Post command.

Fusion takes a RESOURCE FOLDER, not an image: it looks inside for 16x16.png,
32x32.png and the @2x variants, and picks per display scale. A command with no
resource folder gets no icon, and a command with no icon cannot be pinned to
the toolbar - which is the whole reason this exists.

Generated rather than drawn so the icon is reproducible and tweakable:

    python3 tools/fusion-addin/make_icons.py
"""

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent / "RWFPostCheck" / "resources" / "CheckPost"

# A tick, as two strokes in a unit square. Reads at 16 px, which is the only
# size that really has to work.
# Down-and-right to a LOW vertex, then up-and-right on a longer arm. Put the
# vertex high and you get a chevron, not a tick.
STROKES = [((0.18, 0.52), (0.40, 0.27)),
           ((0.40, 0.27), (0.82, 0.76))]
WIDTH = 0.145
COLOUR = (0x1F, 0x9D, 0x55)   # green: this button says "it passed"
SS = 4                        # supersampling per axis


def _dist_to_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def _coverage(col, row, size):
    """Fraction of this pixel covered, by supersampling. Round caps and joins
    fall out of using distance-to-segment.

    Sample offsets are a fraction of ONE PIXEL - (sx + 0.5) / (SS * size) -
    not a fraction of the unit square, or every sample spreads across the whole
    icon and the result is a faint smear."""
    hits = 0
    for sy in range(SS):
        for sx in range(SS):
            x = (col + (sx + 0.5) / SS) / size
            # PNG rows run top-down; the strokes are described bottom-up
            y = 1.0 - (row + (sy + 0.5) / SS) / size
            for (ax, ay), (bx, by) in STROKES:
                if _dist_to_segment(x, y, ax, ay, bx, by) <= WIDTH / 2:
                    hits += 1
                    break
    return hits / (SS * SS)


def _png(path, size):
    rows = []
    for row in range(size):
        out = bytearray()
        for col in range(size):
            a = _coverage(col, row, size)
            out += bytes((*COLOUR, int(round(a * 255))))
        rows.append(bytes(out))

    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    blob = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))
    path.write_bytes(blob)
    return len(blob)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # @2x variants matter on a Retina Mac; without them the icon is resampled
    # from the small one and looks muddy.
    for name, size in [("16x16", 16), ("16x16@2x", 32),
                       ("32x32", 32), ("32x32@2x", 64),
                       ("64x64", 64)]:
        n = _png(OUT / f"{name}.png", size)
        print(f"  {name}.png  {size}x{size}  {n:,} bytes")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
