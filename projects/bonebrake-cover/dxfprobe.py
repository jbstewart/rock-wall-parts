#!/usr/bin/env python3
"""Isolation tests for a DXF region Fusion refuses to profile.

Every file-level property of the coupon measures clean (loops closed, no
crossings, no near-touches between loops, no sub-kerf entities, endpoint gaps
at 1e-9) yet Fusion will not extrude one region. These writes change ONE
variable at a time so the cause can be cornered by experiment instead of
theory:

  -POLY        every closed loop re-emitted as ONE closed LWPOLYLINE, flattened
               at CHORD. Removes splines, multi-entity joining and every
               endpoint question in a single step. If this profiles, the file's
               geometry was never the problem — its curve representation was.
  -ONLY<n>     one loop alone in an otherwise empty file, still as splines.
               If a lone loop will not profile, the defect is in that loop; if
               it will, the defect is interaction with its surroundings.
  -ONLY<n>POLY both at once.

    .venv/bin/python projects/bonebrake-cover/dxfprobe.py <dxf> [loop_index ...]

Nothing here is a cut program; filenames say DIAGNOSTIC.
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

import ezdxf

FLAT = 2e-6      # flattening used to build the loop chains
CHORD = 0.002    # polyline chord tolerance — 27x under a 0.055 kerf


def entity_points(e):
    t = e.dxftype()
    if t == "LINE":
        return [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
    if t == "SPLINE":
        return [(p[0], p[1]) for p in e.construction_tool().flattening(FLAT)]
    if t in ("ARC", "CIRCLE"):
        return [(p.x, p.y) for p in e.flattening(FLAT)]
    if t == "LWPOLYLINE":
        # A degenerate spline repaired at export arrives as a polyline; skipping
        # it would break the chain and report its neighbours as loose ends.
        q = [(v[0], v[1]) for v in e.get_points()]
        if e.closed and q and q[0] != q[-1]:
            q.append(q[0])
        return q
    return None


def chain_loops(msp):
    """Loops as (entity indices, polyline points, is_circle)."""
    ents = []
    for i, e in enumerate(msp):
        p = entity_points(e)
        if p and len(p) >= 2:
            standalone = (e.dxftype() == "CIRCLE"
                          or (e.dxftype() == "LWPOLYLINE" and e.closed))
            ents.append((i, e, p, standalone))
    openes = [(i, e, p) for i, e, p, c in ents if not c]
    circles = [(i, e, p) for i, e, p, c in ents if c]

    Q = 1e-6
    def key(p):
        return (round(p[0] / Q), round(p[1] / Q))

    adj = defaultdict(list)
    for n, (i, e, p) in enumerate(openes):
        adj[key(p[0])].append((n, False))
        adj[key(p[-1])].append((n, True))

    used = [False] * len(openes)
    loops = []
    for n0 in range(len(openes)):
        if used[n0]:
            continue
        pts, idxs = [], []
        n, rev = n0, False
        while True:
            used[n] = True
            i, e, p = openes[n]
            idxs.append(i)
            seg = p[::-1] if rev else p
            pts.extend(seg[1:] if pts else seg)
            nxt = [(m, r) for m, r in adj[key(seg[-1])] if not used[m]]
            if not nxt:
                break
            n, rev = nxt[0]
        if len(pts) >= 3:
            loops.append((idxs, pts, False))
    for i, e, p in circles:
        loops.append(([i], p, True))
    return loops


def densify(pts, chord):
    """Resample a loop so no chord exceeds `chord`, dropping collinear runs."""
    out = [pts[0]]
    for q in pts[1:]:
        if math.dist(out[-1], q) >= chord:
            out.append(q)
    if math.dist(out[0], out[-1]) < chord and len(out) > 3:
        out.pop()
    return out


def main() -> int:
    src = Path(sys.argv[1])
    want = [int(a) for a in sys.argv[2:]]
    doc = ezdxf.readfile(str(src))
    msp = doc.modelspace()
    loops = chain_loops(msp)
    print(f"{src.name}: {len(loops)} loops")
    for li, (idxs, pts, circ) in enumerate(loops):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        per = sum(math.dist(pts[k], pts[(k + 1) % len(pts)])
                  for k in range(len(pts)))
        if per > 5.0 or li in want:
            print(f"  loop {li:>3}: {len(idxs):>3} entities  perim {per:7.3f}  "
                  f"x[{min(xs):+.3f},{max(xs):+.3f}] y[{min(ys):+.3f},{max(ys):+.3f}]")

    stem = src.stem

    def write_poly(path, keep=None):
        out = ezdxf.new(dxfversion="AC1027")
        out.header["$INSUNITS"] = 1
        om = out.modelspace()
        n = 0
        for li, (idxs, pts, circ) in enumerate(loops):
            if keep is not None and li not in keep:
                continue
            p = densify(pts, CHORD)
            om.add_lwpolyline(p, close=True)
            n += 1
        out.saveas(str(path))
        print(f"wrote {path.name}  ({n} closed LWPOLYLINEs, chord {CHORD})")

    def write_subset(path, keep):
        out = ezdxf.new(dxfversion="AC1027")
        out.header["$INSUNITS"] = 1
        om = out.modelspace()
        src_ents = list(msp)
        n = 0
        for li, (idxs, pts, circ) in enumerate(loops):
            if li not in keep:
                continue
            for i in idxs:
                om.add_foreign_entity(src_ents[i], copy=True)
                n += 1
        out.saveas(str(path))
        print(f"wrote {path.name}  ({n} original entities)")

    d = src.parent
    write_poly(d / f"{stem}-POLY-DIAGNOSTIC.dxf")
    for li in want:
        write_subset(d / f"{stem}-ONLY{li}-DIAGNOSTIC.dxf", {li})
        write_poly(d / f"{stem}-ONLY{li}POLY-DIAGNOSTIC.dxf", {li})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
