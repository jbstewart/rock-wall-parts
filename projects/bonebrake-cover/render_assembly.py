"""Customer-facing render of the Bonebrake cover assembly.

Rebuilds the parts through bonebrake_assembly's own functions (same geometry,
same colors as the STEP), tessellates them, and shades a 3/4 view with a
simple lambert model. Output PNG is a presentation aid, NOT a fab document —
renders are gitignored per repo policy.

Run:  ../../.venv/bin/python render_assembly.py
"""

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

import bonebrake_assembly as ba  # noqa: E402

OUT_PNG = ba.OUT_DIR / f"{ba.BASENAME}-render-{ba.REV_TAG}.png"

# Lambert light from the viewer's upper left, in model coords (x right,
# y up the wall, z out of the brick).
LIGHT = np.array([-0.35, 0.45, 1.0])
LIGHT /= np.linalg.norm(LIGHT)
AMBIENT = 0.42


def mesh(shape):
    """Triangles in INCHES from a shape placed in mm.

    Everything here is placed through bonebrake_assembly.place(), which works
    in mm (STEP units), so the tolerances are mm too and the result converts
    back to inches for plotting.
    """
    last = None
    for tol in (0.02, 0.05, 0.1, 0.2):
        try:
            verts, tris = shape.tessellate(tol * ba.IN)
            v = np.array([(p.X, p.Y, p.Z) for p in verts]) / ba.IN
            return v[np.array(tris)]
        except Exception as e:  # noqa: BLE001 — retry coarser
            last = e
    raise last


def subdivide(tris, max_edge=1.25):
    """Split triangles until no edge exceeds max_edge — painter's-algorithm
    depth sorting misorders LARGE coplanar triangles 0.125" apart at glancing
    views (the face/middle z-fight), so feed it small ones."""
    tris = tris.copy()
    for _ in range(12):
        e = np.stack([
            np.linalg.norm(tris[:, 1] - tris[:, 0], axis=1),
            np.linalg.norm(tris[:, 2] - tris[:, 1], axis=1),
            np.linalg.norm(tris[:, 0] - tris[:, 2], axis=1),
        ], axis=1)
        big = e.max(axis=1) > max_edge
        if not big.any():
            break
        keep, split = tris[~big], tris[big]
        longest = e[big].argmax(axis=1)
        a = split[np.arange(len(split)), longest]
        b = split[np.arange(len(split)), (longest + 1) % 3]
        c = split[np.arange(len(split)), (longest + 2) % 3]
        mid = (a + b) / 2
        t1 = np.stack([a, mid, c], axis=1)
        t2 = np.stack([mid, b, c], axis=1)
        tris = np.concatenate([keep, t1, t2])
    return tris


def shaded_colors(tris, rgb):
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    n = np.cross(b - a, c - a)
    norm = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, norm, out=np.zeros_like(n), where=norm > 0)
    lam = AMBIENT + (1 - AMBIENT) * np.abs(n @ LIGHT)
    return np.clip(np.array(rgb)[None, :] * lam[:, None], 0, 1)


def main() -> None:
    print(f"render — Rev {ba.REV}")
    art = ba.artwork_face()
    stack_top = ba.FRAME_T + 2 * ba.PANEL_T

    # Place every part through the assembly's OWN place() helper, so the render
    # and the STEP cannot disagree about where anything sits.
    #
    # This used to re-derive the placements here, converting the catalog
    # fasteners with `shape.scale(1/IN)`. That is the trap AGENTS.md names:
    # scaling a LOCATED shape scales about the local frame and strands the
    # location, which parked every bolt and rivet 4.075" behind the cover. In
    # a 3/4 view that depth error reads as a sideways one — the hardware drew
    # outside the panel's left edge, and it was wrong in the Rev B render too.
    placed = [
        ba.place(ba.build_frame(), 0, 0, 0, "frame"),
        ba.place(ba.build_panel("middle"), 0, 0, ba.FRAME_T, "middle"),
        ba.place(ba.build_panel("face", art=art), 0, 0, stack_top - ba.PANEL_T, "face"),
        *ba.build_fasteners(stack_top=stack_top),
    ]
    if not ba.COUPON:
        # Rev C floor base. Tapcons are deliberately left out — they sit behind
        # the frame against the brick, and this render is for Michelle's finish
        # choice, not for the installer.
        placed.append(ba.place(ba.base_bar(lower=True), 0, -ba.H / 2 - ba.BASE_T, 0, "base-lower"))
        placed.append(ba.place(ba.base_bar(lower=False), 0, -ba.H / 2 - ba.FRAME_T, 0, "base-upper"))
    parts = [(p, p.label.rstrip("0123456789")) for p in placed]

    fig = plt.figure(figsize=(6, 14), dpi=220)
    ax = fig.add_subplot(111, projection="3d", proj_type="ortho")
    # The assembly is literally a stack of layers 0.125" apart — per-triangle
    # depth sorting can't resolve that at an oblique view (tried; z-fight
    # artifacts), so we dictate the paint order ourselves: brick-side out.
    ax.computed_zorder = False
    # The base projects 1.5" toward the viewer at the bottom of the piece, so
    # it paints last — at this elevation its front edge rides up over the face
    # panel's bottom edge in projection.
    order = {"frame": 0, "middle": 1, "face": 2, "screw": 3, "rivet": 3,
             "base-lower": 4, "base-upper": 4}
    for shape, key in sorted(parts, key=lambda p: order[p[1]]):
        tris = mesh(shape)
        rgb = tuple(ba.COLORS[key])[:3]  # Color iterates as (r, g, b, a)
        cols = shaded_colors(tris, rgb)
        ax.add_collection3d(Poly3DCollection(
            tris[:, :, [0, 2, 1]],  # plot coords: (x, z, y) so wall-Y draws vertical
            facecolors=cols, edgecolors=cols, linewidths=0.25,  # edge=face color
            zsort="average",                                    # fills AA seam cracks
        ))
        print(f"  {key}: {len(tris)} tris")

    wx = ba.W / 2 + 0.8
    y_hi = ba.H / 2 + 0.8
    y_lo = -(ba.H / 2 + ba.BASE_T) - 0.8   # room for the base below the frame
    ax.set_xlim(-wx, wx)
    ax.set_ylim(-1.5, 2.5)
    ax.set_zlim(y_lo, y_hi)
    ax.set_box_aspect((2 * wx, 4.0, y_hi - y_lo))
    ax.view_init(elev=7, azim=-76)
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(OUT_PNG, facecolor="white", bbox_inches="tight", pad_inches=0.1)
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
