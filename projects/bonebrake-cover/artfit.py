#!/usr/bin/env python3
"""Artwork-fit diagnostic — the panel with the art at FULL FIT and every
fastener keep-out drawn, so artwork edits can be measured against real geometry.

Why this exists: the released panel DXF carries the art at whatever scale the
auto-backoff settled on (Rev D: 0.0172, down from a 0.0198 max fit). Editing the
SVG against that file and reasoning in those coordinates moves features by the
wrong amount in the wrong direction — it happened once, on Rev-03, which pushed
a branch INTO bolt (-3.500,-6.604) instead of away from it. This file shows the
art at the size it would be if nothing had to back off, with three rings per
hole, so "which feature hits what, and which way does it go" is readable.

NOT a cut program. Nothing here is a release output; filenames say DIAGNOSTIC.

Layers:
  PANEL      panel outline, true size
  ART        the art at FULL FIT (max scale, despiked) — the goal, not Rev D
  HOLE       final drilled hole, as-built size
  KEEPOUT    hole + 0.05 margin — what the generation check gates on
  WEBTARGET  hole + half kerf + MIN_WEB — clear this and the web is sound
  VIOLATION  a cross at each art point that is inside its WEBTARGET ring

    .venv/bin/python projects/bonebrake-cover/artfit.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bonebrake_assembly as ba  # noqa: E402
from build123d import (  # noqa: E402
    Circle,
    Compound,
    Edge,
    Pos,
    RectangleRounded,
    Unit,
)
from build123d.exporters import ColorIndex, ExportDXF  # noqa: E402

OUT_DXF = ba.OUT_DIR / f"{ba.BASENAME}-artfit-DIAGNOSTIC.dxf"
OUT_MD = ba.OUT_DIR / f"{ba.BASENAME}-artfit-DIAGNOSTIC.md"


def full_fit_art():
    """The art scaled as large as it fits, despiked, with no clearance backoff."""
    art_file = ba.art_finals()[0]
    faces = ba.load_art_faces(art_file)
    raw = faces[0] if len(faces) == 1 else Compound(children=faces)
    bb = raw.bounding_box()
    s = min((ba.W - 2 * ba.ART_MARGIN) / bb.size.X,
            (ba.H - 2 * ba.ART_BAND) / bb.size.Y)
    a = raw.scale(s)
    c = a.bounding_box().center()
    art, log, left, _ = ba.despike_art(Pos(-c.X, -c.Y) * a)
    return art, s, art_file, log, left


def holes():
    """Every fastener hole in the panel, as (centre, final drilled dia, role)."""
    return ([(p, ba.BOLT_CLEAR_DIA, "bolt") for p in ba.corner_pattern()]
            + [(p, ba.RIVET_HOLE_DIA, "rivet") for p in ba.rivet_pattern()])


def nearest_art(art, hx, hy, reach=0.9):
    """Closest point on the art boundary to a hole centre, and its distance."""
    best = None
    for f in art.faces():
        for w in f.wires():
            for e in w.edges():
                bb = e.bounding_box()
                if (bb.min.X - hx > reach or hx - bb.max.X > reach
                        or bb.min.Y - hy > reach or hy - bb.max.Y > reach):
                    continue
                n = max(8, int(e.length / 0.001))
                for t in range(n + 1):
                    q = e @ (t / n)
                    d = math.hypot(q.X - hx, q.Y - hy)
                    if best is None or d < best[0]:
                        best = (d, q)
    return best


def main() -> int:
    art, scale, art_file, log, left = full_fit_art()
    trimmed = [r for r in log if r[0] == "trimmed"]
    print(f"Bonebrake artwork-fit diagnostic — {art_file.name}")
    print(f"  full-fit scale {scale:.4f}  (Rev {ba.REV} ships whatever the "
          f"backoff settles on — run the generator to see it)")
    print(f"  cusp spikes trimmed {len(trimmed)}, unrepaired {len(left)}")

    rows = []
    for (hx, hy), dia, role in holes():
        r = dia / 2
        keepout = r + 0.05
        webtarget = r + ba.PLASMA_KERF / 2 + ba.MIN_WEB
        near = nearest_art(art, hx, hy)
        if near is None:
            # No art within the search radius. Say so; dropping the row would
            # make a complete-looking table that silently omits holes.
            rows.append({
                "x": hx, "y": hy, "dia": dia, "role": role, "d": None, "p": None,
                "keepout": keepout, "webtarget": webtarget, "web": None,
                "ux": 0.0, "uy": 0.0,
            })
            continue
        d, p = near
        rows.append({
            "x": hx, "y": hy, "dia": dia, "role": role, "d": d, "p": p,
            "keepout": keepout, "webtarget": webtarget,
            "web": d - r - ba.PLASMA_KERF / 2,
            "ux": (p.X - hx) / d, "uy": (p.Y - hy) / d,
        })
    rows.sort(key=lambda z: 1e9 if z["d"] is None else z["d"] - z["webtarget"])

    # ---------------------------------------------------------------- DXF
    ex = ExportDXF(unit=Unit.IN)
    ex.add_layer("PANEL", color=ColorIndex.GRAY)
    ex.add_layer("ART", color=ColorIndex.GREEN)
    ex.add_layer("HOLE", color=ColorIndex.CYAN)
    ex.add_layer("KEEPOUT", color=ColorIndex.YELLOW)
    ex.add_layer("WEBTARGET", color=ColorIndex.BLUE)
    ex.add_layer("VIOLATION", color=ColorIndex.RED)
    ex.add_shape(RectangleRounded(ba.W, ba.H, ba.CORNER_R), layer="PANEL")
    ex.add_shape(art, layer="ART")
    for z in rows:
        c = Pos(z["x"], z["y"])
        ex.add_shape(c * Circle(z["dia"] / 2), layer="HOLE")
        ex.add_shape(c * Circle(z["keepout"]), layer="KEEPOUT")
        ex.add_shape(c * Circle(z["webtarget"]), layer="WEBTARGET")
        if z["web"] is not None and z["web"] < ba.MIN_WEB:
            px, py, k = z["p"].X, z["p"].Y, 0.06
            ex.add_shape(Edge.make_line((px - k, py, 0), (px + k, py, 0)),
                         layer="VIOLATION")
            ex.add_shape(Edge.make_line((px, py - k, 0), (px, py + k, 0)),
                         layer="VIOLATION")
    ba.OUT_DIR.mkdir(parents=True, exist_ok=True)
    ex.write(str(OUT_DXF))
    print(f"\nwrote {OUT_DXF.name}")

    # ---------------------------------------------------------------- report
    bad = [z for z in rows if z["web"] is not None and z["web"] < ba.MIN_WEB]
    ab = art.bounding_box()
    L = []
    L.append(f"# Bonebrake artwork-fit diagnostic — {art_file.name}")
    L.append("")
    L.append(f"Full-fit scale **{scale:.4f}**. Not a cut program — a reference for editing the SVG.")
    L.append("")
    L.append(f"The released panel DXF carries the art at the auto-backoff scale, which is SMALLER than this. Measure artwork edits against THIS file, never against the released panel: a delta read off the backed-off art is the wrong size and, if the feature has moved around the hole, the wrong direction.")
    L.append("")
    L.append(f"Cusp spikes trimmed at full fit: **{len(trimmed)}**, unrepaired: **{len(left)}**.")
    L.append("")
    L.append(f"`MIN_WEB` {ba.MIN_WEB:.4f} · kerf {ba.PLASMA_KERF:.3f} · keep-out margin 0.05")
    L.append("")
    L.append("## Clearance at full fit, worst first")
    L.append("")
    L.append("| hole | role | dia | art edge from centre | keep-out | post-kerf web | verdict |")
    L.append("|---|---|---|---|---|---|---|")
    for z in rows:
        if z["d"] is None:
            L.append(f"| ({z['x']:+.3f}, {z['y']:+.3f}) | {z['role']} | {z['dia']:.4f} "
                     f"| no art within 0.9 | {z['keepout']:.4f} | — | clear |")
            continue
        if z["d"] < z["keepout"]:
            v = "**INVADES KEEP-OUT**"
        elif z["web"] < ba.MIN_WEB:
            v = "under MIN_WEB"
        else:
            v = "ok"
        L.append(f"| ({z['x']:+.3f}, {z['y']:+.3f}) | {z['role']} | {z['dia']:.4f} "
                 f"| {z['d']:.4f} | {z['keepout']:.4f} | {z['web']:+.4f} | {v} |")
    L.append("")
    if bad:
        L.append("## What to move, and which way")
        L.append("")
        L.append("Directions are the vector **away from the hole centre**. SVG y is flipped "
                 "(`flip_y=True`), so a positive `dy_svg` moves the feature DOWN on the finished "
                 "panel and DOWN on screen in the editor.")
        L.append("")
        L.append("| hole | art point (panel) | normalized LL (u, v) | to clear keep-out | to reach MIN_WEB |")
        L.append("|---|---|---|---|---|")
        for z in bad:
            u = (z["p"].X - ab.min.X) / ab.size.X
            v = (z["p"].Y - ab.min.Y) / ab.size.Y
            n1 = z["keepout"] - z["d"]
            n2 = z["webtarget"] - z["d"]
            def fmt(need):
                return (f"{need:+.4f}\" → dx {z['ux'] * need / scale:+.2f}, "
                        f"dy_svg {-z['uy'] * need / scale:+.2f} svg units")
            L.append(f"| ({z['x']:+.3f}, {z['y']:+.3f}) | ({z['p'].X:+.4f}, {z['p'].Y:+.4f}) "
                     f"| (u {u:.4f}, v {v:.4f}) | {fmt(n1)} | {fmt(n2)} |")
        L.append("")
    L.append("## Layers")
    L.append("")
    L.append("`PANEL` outline · `ART` full-fit art · `HOLE` as-built drilled hole · "
             "`KEEPOUT` hole + 0.05 (what the check gates) · `WEBTARGET` hole + half kerf + "
             "`MIN_WEB` (clear this and the web is sound) · `VIOLATION` cross at each art point "
             "inside its WEBTARGET ring.")
    L.append("")
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT_MD.name}")

    print(f"\n{'hole':>18} {'role':>6} {'art edge':>9} {'keepout':>8} {'web':>8}  verdict")
    for z in rows:
        if z["d"] is None:
            print(f"  ({z['x']:+.3f},{z['y']:+.3f}) {z['role']:>6} {'  >0.9':>9} "
                  f"{z['keepout']:8.4f} {'   —':>8}  clear")
            continue
        v = ("INVADES KEEP-OUT" if z["d"] < z["keepout"]
             else "under MIN_WEB" if z["web"] < ba.MIN_WEB else "ok")
        print(f"  ({z['x']:+.3f},{z['y']:+.3f}) {z['role']:>6} {z['d']:9.4f} "
              f"{z['keepout']:8.4f} {z['web']:+8.4f}  {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
