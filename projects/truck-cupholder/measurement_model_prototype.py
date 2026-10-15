"""PROTOTYPE — typed measurements with provenance and cross-field consistency.

Not wired into truck_cupholder.py. This exists to answer one question: would a
typed measurement model have caught the transcription errors that cost this job
several revisions? It replays the worksheet EXACTLY as first filled in
(2026-08-30) and then the corrected set, and reports what each one trips.

If this earns its keep, the model graduates to lib/measurements.py when a second
job adopts it (house rule: generalize on the second use, not the first).

Run:  ../../.venv/bin/python measurement_model_prototype.py
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

Source = Literal["measured", "drawing", "derived", "assumed", "vendor"]

# Tolerances for the consistency relations below. Generous — these checks exist
# to catch transcription blunders (a factor of 10, a misread datum), not to
# adjudicate whether a caliper read 0.501 or 0.499.
STACK_TOL = 0.02


class M(BaseModel):
    """One dimension, in inches, carrying where it came from.

    Supports float() so call sites read like today's bare constants:
        PLUG_R = float(m.hole_d) / 2 - 0.03
    """

    model_config = {"frozen": True}

    value: float
    source: Source
    on: str = ""             # ISO date the value was established
    note: str = ""

    def __float__(self) -> float:
        return self.value

    def __repr__(self) -> str:
        tag = self.source if not self.on else f"{self.source} {self.on}"
        return f"{self.value:g}″ ({tag})"


class SeatRecess(BaseModel):
    """The measurable facts about the truck seat. Every relation below is a
    PHYSICAL one — it constrains the real object, not our design choices."""

    # --- the pocket ---
    recess_depth: M
    hole_d: M                 # recess/plate opening circle diameter
    fabric_l: M
    fabric_w: M

    # --- the retention plate buried in the foam ---
    plate_top: M              # upholstery top -> TOP of plate
    plate_thickness: M
    plate_underside: M        # upholstery top -> UNDERSIDE of plate (the hook ledge)

    # --- the OEM insert we're replacing ---
    oem_flange_t: M
    oem_tub_depth: M          # flange underside -> outside bottom

    # --- the cup ---
    cup_base_d: M
    cup_taper_top_d: M
    cup_taper_h: M
    cup_rim_d: M
    cup_h: M

    @model_validator(mode="after")
    def physical_relations_hold(self) -> "SeatRecess":
        """All relations in one pass — a bad worksheet usually has more than one
        error, and fail-fast would hide the rest behind the first."""
        f = float
        bad: list[str] = []

        top, thick, under = f(self.plate_top), f(self.plate_thickness), f(self.plate_underside)
        if abs(under - (top + thick)) > STACK_TOL:
            bad.append(
                f"plate stack does not close: top {top:.4f} + thickness {thick:.4f} "
                f"= {top + thick:.4f}, but underside was recorded as {under:.4f} "
                f"(off by {abs(under - (top + thick)):.4f}). One of the three is wrong — "
                "and 'underside' is the one the snap hooks bear on."
            )

        if under >= f(self.recess_depth):
            bad.append(
                f"hook ledge {under:.3f} is at or below the recess floor "
                f"{f(self.recess_depth):.3f} — nothing could latch under it"
            )

        # A trim flange sits ON the upholstery; it cannot be a sizable fraction
        # of the pocket it covers. This is the decimal-point tripwire.
        if f(self.oem_flange_t) > 0.5 * f(self.recess_depth):
            bad.append(
                f"flange thickness {f(self.oem_flange_t):.3f} is more than half the recess "
                f"depth {f(self.recess_depth):.3f} — implausible for a trim flange. "
                "Misplaced decimal, or a different feature was measured?"
            )

        if f(self.oem_tub_depth) > f(self.recess_depth) + STACK_TOL:
            bad.append(
                f"OEM tub depth {f(self.oem_tub_depth):.3f} exceeds recess depth "
                f"{f(self.recess_depth):.3f} — the part cannot be deeper than the hole it "
                "sits in. Likely measured from a different datum."
            )

        base, mid, rim = f(self.cup_base_d), f(self.cup_taper_top_d), f(self.cup_rim_d)
        if not base <= mid <= rim:
            bad.append(
                f"cup diameters not monotonic bottom-to-top: base {base}, taper top {mid}, "
                f"rim {rim}"
            )
        if f(self.cup_taper_h) >= f(self.cup_h):
            bad.append(
                f"cup taper height {f(self.cup_taper_h)} >= overall height {f(self.cup_h)}"
            )

        if bad:
            raise ValueError("; ".join(bad))
        return self

    def assumptions(self) -> list[str]:
        """Values not actually measured — the ones a check can silently rest on."""
        return [
            f"{name}: {getattr(self, name)!r}"
            for name in type(self).model_fields
            if getattr(self, name).source == "assumed"
        ]


# --------------------------------------------------------------- the two sets

# Exactly as Brian first filled out MEASUREMENTS.md, before any correction.
AS_FIRST_ENTERED = dict(
    recess_depth=M(value=0.75, source="measured", on="2026-08-30"),
    hole_d=M(value=3.96, source="drawing", on="2026-08-30", note="7.71 overall - 3.75 c-c"),
    fabric_l=M(value=7.75, source="measured", on="2026-08-30"),
    fabric_w=M(value=4.0, source="measured", on="2026-08-30"),
    plate_top=M(value=11 / 32, source="measured", on="2026-08-30"),
    plate_thickness=M(value=1 / 8, source="measured", on="2026-08-30"),
    plate_underside=M(value=1 / 16, source="measured", on="2026-08-30"),
    oem_flange_t=M(value=1.32, source="measured", on="2026-08-30"),
    oem_tub_depth=M(value=2.0, source="measured", on="2026-08-30"),
    cup_base_d=M(value=2.8, source="measured", on="2026-08-30"),
    cup_taper_top_d=M(value=3.5, source="measured", on="2026-08-30"),
    cup_taper_h=M(value=3.45, source="measured", on="2026-08-30"),
    cup_rim_d=M(value=4.0, source="assumed", on="2026-08-30", note="not yet measured at Rev A"),
    cup_h=M(value=7.9, source="assumed", on="2026-08-30", note="typical 30 oz"),
)

# After the corrections that took Rev A -> Rev D to discover.
AS_CORRECTED = AS_FIRST_ENTERED | dict(
    plate_underside=M(value=0.50, source="measured", on="2026-08-30",
                      note="Brian's correction; supersedes the 1/16 reading"),
    oem_flange_t=M(value=0.132, source="measured", on="2026-08-30",
                   note="1.32 was the formed-flange height, a different feature"),
    oem_tub_depth=M(value=0.70, source="derived", on="2026-08-30",
                    note="2.0 was top-of-tub to bottom, not below-flange"),
    cup_rim_d=M(value=4.0, source="measured", on="2026-08-30"),
    cup_h=M(value=8.0, source="measured", on="2026-08-30"),
)


def report(label: str, data: dict) -> None:
    print(f"\n=== {label} " + "=" * max(0, 58 - len(label)))
    try:
        seat = SeatRecess(**data)
    except ValidationError as e:
        for err in e.errors():
            for failure in err["msg"].removeprefix("Value error, ").split("; "):
                print(f"  [CAUGHT] {failure}")
        return
    print("  [OK] every physical relation closes")
    todo = seat.assumptions()
    if todo:
        print("  [ASSUMED — not measured, a check may be resting on these]")
        for a in todo:
            print(f"          {a}")
    print(f"  usable directly: hole radius = {float(seat.hole_d) / 2:.3f}″")


if __name__ == "__main__":
    print("Typed-measurement prototype — replaying the cup holder's worksheet history")
    report("AS FIRST ENTERED (Rev A worksheet, uncorrected)", AS_FIRST_ENTERED)
    report("AS CORRECTED (the values Rev D runs on)", AS_CORRECTED)
