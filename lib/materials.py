"""Shop material price book — unit prices for BOM cost rollups.

Update prices when suppliers change them; date the change in a comment.
(This file is the seed of the Platypus Jobs "Material Price Book" concept —
same data shape, dogfooded here first.)
"""

MATERIALS: dict[str, dict] = {
    "flat_bar_1_4x1_5": {
        "desc": '1/4" x 1-1/2" mild steel flat bar',
        "unit": "ft",
        "price": 1.13,  # 2026-08-25
    },
    "sheet_11ga": {
        "desc": "11ga mild steel sheet",
        "unit": "sqft",
        "price": 8.44,  # 2026-08-25
    },
}


def cost(key: str, qty: float) -> float:
    return MATERIALS[key]["price"] * qty
