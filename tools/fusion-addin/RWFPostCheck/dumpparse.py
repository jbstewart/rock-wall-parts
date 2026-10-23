"""Parse the text files written by Fusion's CAM_API_Utilities "Export Parameters".

Only used offline: it lets the rules in rules.py be tested against real dumps,
and lets a setup be checked from a saved dump without opening Fusion. The
add-in itself reads the live API, not these files.
"""

from __future__ import annotations

import re
from pathlib import Path

from rules import Chain

# Operation headers carry a trailing strategy clause that setup and tool
# headers do not:
#   == Parameter information for operation "Small Holes" using strategy "profile2d". ==
HEADER = re.compile(
    r'^== Parameter information for (\w+) "([^"]*)"'
    r'(?: using strategy "([^"]*)")?\.? =='
)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _coerce(raw: str, vtype: str):
    raw = raw.strip()
    if vtype == "StringParameterValue":
        return raw
    if raw == "True":
        return True
    if raw == "False":
        return False
    try:
        return float(raw)
    except ValueError:
        return raw


def _parse_chains(body: list[str]) -> list[Chain]:
    """Pull ChainSelection blocks out of a CadContours2dParameterValue body.

    One chain is one contour. A chain holds several edges - a circle comes back
    as two BRepEdges - so chains are what get counted, never edges."""
    chains: list[Chain] = []
    current: Chain | None = None
    in_geom = False
    for line in body:
        stripped = line.strip()
        if not stripped:
            continue
        ind = _indent(line)
        if "ChainSelection" in stripped and stripped.startswith("Curve Selection"):
            current = Chain()
            chains.append(current)
            in_geom = False
            continue
        if current is None:
            continue
        if stripped == "inputGeometry:":
            in_geom = True
            geom_indent = ind
            continue
        if in_geom:
            # geometry class names sit one level in from "inputGeometry:"
            if ind > geom_indent:
                current.geometry.append(stripped)
                continue
            in_geom = False
        if stripped.startswith("isOpen:"):
            current.is_open = stripped.split(":", 1)[1].strip() == "True"
    return chains


def parse(path: str | Path) -> dict:
    """Return {"kind": "setup"|"operation"|"tool", "name": str, "strategy": str|None,
    "params": {...}, "contours": [Chain, ...]}."""
    lines = Path(path).read_text().splitlines()

    kind, name, strategy = "unknown", Path(path).stem, None
    for line in lines[:5]:
        m = HEADER.match(line)
        if m:
            kind, name, strategy = m.group(1), m.group(2), m.group(3)
            break

    # split into per-parameter blocks on the zero-indent "name:" lines
    blocks: list[tuple[str, list[str]]] = []
    key, body = None, []
    for line in lines:
        if line.startswith("name: "):
            if key is not None:
                blocks.append((key, body))
            key, body = line[6:].strip(), []
        elif key is not None:
            body.append(line)
    if key is not None:
        blocks.append((key, body))

    params: dict = {}
    contours: list[Chain] = []
    for pname, body in blocks:
        vtype = None
        for line in body:
            s = line.strip()
            if s.endswith("ParameterValue") and _indent(line) == 4:
                vtype = s
                break
        if vtype == "CadContours2dParameterValue":
            contours = _parse_chains(body)
            params[pname] = f"{len(contours)} chain(s)"
            continue
        for i, line in enumerate(body):
            s = line.strip()
            if s.startswith("value:") and _indent(line) == 8:
                inline = s[6:].strip()
                if inline:
                    params[pname] = _coerce(inline, vtype or "")
                else:
                    # CadObjectParameterValue lists its entities on the lines
                    # below instead of inline; an unset one reads "Empty".
                    deeper = []
                    for nxt in body[i + 1:]:
                        if not nxt.strip():
                            continue
                        if _indent(nxt) <= 8:
                            break
                        deeper.append(nxt.strip())
                    params[pname] = ", ".join(deeper)
                break

    return {"kind": kind, "name": name, "strategy": strategy,
            "params": params, "contours": contours}
