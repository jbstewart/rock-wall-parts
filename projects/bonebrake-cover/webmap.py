"""Artwork cut-density diagnostic — where the plasma cuts crowd each other.

Not a fab document. This exists for the artwork iteration loop: edit the SVG,
run this, see what moved. The measurement lives in bonebrake_assembly
(thin_features) so this can never disagree with the gating checks.

Locations are given as (u, v) normalised to the ARTWORK bounding box with the
origin at LOWER LEFT — an SVG carries no dimensions, so (u, v) is the only
coordinate that survives the round trip into a drawing program.

Run:  .venv/bin/python projects/bonebrake-cover/webmap.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as MplCircle

import bonebrake_assembly as ba

OUT = ba.OUT_DIR / "bonebrake-webmap-DIAGNOSTIC.png"


def contour_xy(wire, step=0.01):
    xs, ys = [], []
    for e in wire.edges():
        n = max(2, int(e.length / step))
        for i in range(n + 1):
            p = e.position_at(min(1.0, i / n))
            xs.append(p.X); ys.append(p.Y)
    return xs, ys


def draw(ax, face, cuts, xlim=None, ylim=None, label_pts=True):
    for w in [face.outer_wire(), *face.inner_wires()]:
        xs, ys = contour_xy(w)
        ax.plot(xs, ys, lw=0.5, color="#333333", zorder=2)
    for r in cuts["webs"]:
        ax.add_patch(MplCircle((r["x"], r["y"]), 0.16, fill=False, lw=1.4,
                               color="#d62728", zorder=5))
    for r in cuts["slivers"]:
        ax.add_patch(MplCircle((r["x"], r["y"]), 0.16, fill=False, lw=1.4,
                               color="#ff9900", zorder=4, linestyle=":"))
    if label_pts:
        for r in cuts["webs"]:
            ax.annotate(f"{r['len']:.2f}", (r["x"], r["y"]), textcoords="offset points",
                        xytext=(7, 4), fontsize=5.5, color="#d62728", zorder=6)
        for r in cuts["slivers"]:
            ax.annotate(f"{r['len']:.2f}", (r["x"], r["y"]), textcoords="offset points",
                        xytext=(7, -8), fontsize=5.5, color="#cc6600", zorder=6)
    ax.set_aspect("equal")
    if xlim: ax.set_xlim(*xlim)
    if ylim: ax.set_ylim(*ylim)
    ax.grid(True, lw=0.25, alpha=0.4)


def main():
    art = ba.artwork_face()
    if art is None:
        sys.exit("no artwork found")
    cuts = ba.thin_features(art)
    face = max(ba.panel_sketch(art, pilots=True).faces(), key=lambda f: f.area)

    print(f"\nFLOORS: steel >= {ba.MIN_WEB:.4f} (1x t, 11ga actual)   "
          f"art >= {ba.MIN_SLIVER:.3f} (2x kerf)")
    print(f"GATE:   no too-thin run longer than {ba.MAX_THIN_RUN:.3f}")
    print("\n(u, v) normalised to the ARTWORK bounding box, origin LOWER LEFT.\n")

    for lbl, rows, unit in (
        ("STEEL ribbons thinner than floor", cuts["webs"], "thick"),
        ("ART ribbons narrower than floor", cuts["slivers"], "wide"),
    ):
        print(f"{lbl} — {len(rows)} over {ba.RIBBON_MIN_AREA} in2")
        print(f"   {'run':>6} {unit:>7} {'area':>7}   {'u':>7} {'v':>7}   panel x,y")
        for r in rows:
            flag = "   <-- OVER GATE" if r["len"] > ba.MAX_THIN_RUN else ""
            print(f"   {r['len']:6.3f} {r['thick']:7.4f} {r['area']:7.4f}   "
                  f"{r['u']:7.4f} {r['v']:7.4f}   ({r['x']:+.3f},{r['y']:+.3f}){flag}")
        print()

    print(f"steel under floor: {cuts['web_thin_area']:.4f} in2 "
          f"({100 * cuts['web_thin_area'] / cuts['steel_area']:.2f}% of material) "
          f"in {cuts['web_patches']} patches")
    print(f"art under floor:   {cuts['sliver_thin_area']:.4f} in2 "
          f"({100 * cuts['sliver_thin_area'] / cuts['cut_area']:.2f}% of cutout) "
          f"in {cuts['sliver_patches']} patches")

    if cuts["webs"]:
        ys = sorted(r["y"] for r in cuts["webs"])
        best, best_n = ys[0], 0
        for y0 in ys:
            n = sum(1 for v in ys if y0 <= v < y0 + 2.5)
            if n > best_n:
                best, best_n = y0, n
        print(f"\nDENSEST BAND: {best_n} of {len(cuts['webs'])} ribbons inside "
              f"y {best:+.2f} .. {best + 2.5:+.2f}")
        zoom_y = (best - 0.6, best + 3.1)
    else:
        zoom_y = (-4, 4)

    fig = plt.figure(figsize=(13, 16))
    ax1 = fig.add_subplot(1, 3, 1)
    draw(ax1, face, cuts, label_pts=False)
    ax1.set_title(f"whole face\n{len(cuts['webs'])} steel + {len(cuts['slivers'])} art ribbons",
                  fontsize=9)
    ax2 = fig.add_subplot(1, 3, (2, 3))
    draw(ax2, face, cuts, xlim=(-4.4, 4.4), ylim=zoom_y)
    ax2.set_title(f"densest band  y {zoom_y[0]:+.2f} .. {zoom_y[1]:+.2f}\n"
                  "red = steel under 1x t   orange dotted = art under 2x kerf   "
                  "label = run length",
                  fontsize=9)
    fig.suptitle("Bonebrake face — cut-density diagnostic (NOT a fab document)\n"
                 f"longest steel run {cuts['longest_web_run']:.3f}   "
                 f"longest art run {cuts['longest_sliver_run']:.3f}   "
                 f"gate {ba.MAX_THIN_RUN:.3f}", fontsize=11)
    fig.tight_layout()
    ba.OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
