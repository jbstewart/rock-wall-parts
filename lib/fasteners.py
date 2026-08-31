"""Fastener lookup table — resolves catalog callouts to hole sizes by role.

The drafting "drill chart," as code. All dimensions in inches.

Roles:
  screws: "clearance"        free-fit through-hole (default)
          "clearance_close"  close-fit through-hole
          "tap"              tap drill (~75% thread, coarse series listed)
          "cbore"            (diameter, depth) recess for a socket-head cap screw
  rivets: "clearance"        shank hole through the clamped layers
          "relief"           oversized hole clearing the blind-side bulb

Sources: standard inch drill/tap charts and SHCS counterbore tables. Rivet
bulb/protrusion figures are APPROXIMATE (typical open-end aluminum blind
rivets) — verify against the actual rivet's datasheet before cutting; grip
range is per-SKU and belongs in the project brief, not this table.
"""

from __future__ import annotations

# --------------------------------------------------------------- screws
# head_dia/head_height are simplified button-head model hints, not gospel.
SCREWS: dict[str, dict[str, float]] = {
    "#4-40": {
        "major_dia": 0.112, "tpi": 40,
        "clearance": 0.1285, "clearance_close": 0.116, "tap": 0.089,
        "cbore_dia": 0.219, "cbore_depth": 0.112,
        "head_dia": 0.213, "head_height": 0.054,
    },
    "#6-32": {
        "major_dia": 0.138, "tpi": 32,
        "clearance": 0.1495, "clearance_close": 0.144, "tap": 0.1065,
        "cbore_dia": 0.250, "cbore_depth": 0.138,
        "head_dia": 0.262, "head_height": 0.066,
    },
    "#8-32": {
        "major_dia": 0.164, "tpi": 32,
        "clearance": 0.177, "clearance_close": 0.1695, "tap": 0.136,
        "cbore_dia": 0.281, "cbore_depth": 0.164,
        "head_dia": 0.312, "head_height": 0.078,
    },
    "#10-24": {
        "major_dia": 0.190, "tpi": 24,
        "clearance": 0.201, "clearance_close": 0.196, "tap": 0.1495,
        "cbore_dia": 0.3125, "cbore_depth": 0.190,
        "head_dia": 0.361, "head_height": 0.091,
    },
    "#10-32": {
        "major_dia": 0.190, "tpi": 32,
        "clearance": 0.201, "clearance_close": 0.196, "tap": 0.159,
        "cbore_dia": 0.3125, "cbore_depth": 0.190,
        "head_dia": 0.361, "head_height": 0.091,
    },
    "1/4-20": {
        "major_dia": 0.250, "tpi": 20,
        "clearance": 0.2656, "clearance_close": 0.257, "tap": 0.201,
        "cbore_dia": 0.4375, "cbore_depth": 0.250,
        "head_dia": 0.4375, "head_height": 0.132,
    },
    "1/4-28": {
        "major_dia": 0.250, "tpi": 28,
        "clearance": 0.2656, "clearance_close": 0.257, "tap": 0.213,
        "cbore_dia": 0.4375, "cbore_depth": 0.250,
        "head_dia": 0.4375, "head_height": 0.132,
    },
    "5/16-18": {
        "major_dia": 0.3125, "tpi": 18,
        "clearance": 0.3281, "clearance_close": 0.323, "tap": 0.257,
        "cbore_dia": 0.531, "cbore_depth": 0.3125,
        "head_dia": 0.547, "head_height": 0.166,
    },
    "3/8-16": {
        "major_dia": 0.375, "tpi": 16,
        "clearance": 0.3906, "clearance_close": 0.386, "tap": 0.3125,
        "cbore_dia": 0.625, "cbore_depth": 0.375,
        "head_dia": 0.656, "head_height": 0.199,
    },
}

# --------------------------------------------------------------- blind rivets
# bulb_dia ≈ 1.55 x shank (typical open-end aluminum); relief adds margin.
# protrusion_max = typical worst-case blind-side stick-out — VERIFY per SKU.
RIVETS: dict[str, dict[str, float]] = {
    "3/32": {
        "shank_dia": 0.097, "clearance": 0.100,
        "bulb_dia": 0.150, "relief": 0.190, "protrusion_max": 0.125,
    },
    "1/8": {
        "shank_dia": 0.125, "clearance": 0.129,
        "bulb_dia": 0.195, "relief": 0.235, "protrusion_max": 0.150,
    },
    "5/32": {
        "shank_dia": 0.156, "clearance": 0.161,
        "bulb_dia": 0.242, "relief": 0.290, "protrusion_max": 0.175,
    },
    "3/16": {
        "shank_dia": 0.187, "clearance": 0.194,
        "bulb_dia": 0.290, "relief": 0.340, "protrusion_max": 0.200,
    },
}

# --------------------------------------------------------------- solid rivets
# Bucked (not blind): need back-side access; tail protrusion ~1.5 x dia forms
# the shop head (dia ~1.5d, height ~0.5d). Snug holes — the shank swells to fill.
SOLID_RIVETS: dict[str, dict[str, float]] = {
    "3/16": {
        "shank_dia": 0.1875, "clearance": 0.191,  # drill #11
        "head_dia": 0.406, "head_height": 0.075,  # brazier head
    },
}


# --------------------------------------------------------------- lookups


def screw_hole(callout: str, role: str = "clearance") -> float:
    """Hole diameter for a screw callout. Roles: clearance / clearance_close / tap."""
    spec = SCREWS[callout]
    if role not in ("clearance", "clearance_close", "tap"):
        raise ValueError(f"unknown screw hole role: {role!r}")
    return spec[role]


def screw_cbore(callout: str) -> tuple[float, float]:
    """(diameter, depth) of a socket-head counterbore for a screw callout."""
    spec = SCREWS[callout]
    return spec["cbore_dia"], spec["cbore_depth"]


def rivet_hole(size: str, role: str = "clearance") -> float:
    """Hole diameter for a blind-rivet size. Roles: clearance / relief."""
    spec = RIVETS[size]
    if role not in ("clearance", "relief"):
        raise ValueError(f"unknown rivet hole role: {role!r}")
    return spec[role]


def rivet_protrusion_ok(size: str, relief_depth: float) -> bool:
    """True if the blind-side bulb fits within relief_depth (backer + any gap).

    Uses the table's typical worst-case protrusion — confirm against the
    actual rivet datasheet for anything structural.
    """
    return RIVETS[size]["protrusion_max"] <= relief_depth
