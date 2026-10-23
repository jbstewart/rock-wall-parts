"""Run the shop rules against real Export Parameters dumps.

The fixtures are the genuine article, exported from the arcdroid-coupons
Fusion document on 2026-10-22. One of them - op-other-holes-sketch-selected.txt -
is the live defect state that was sitting in the file that evening: an
operation whose contours had reverted to sketch curves, which is how the holes
came to cut clockwise. It is kept as a regression fixture precisely because it
is wrong.

    python3 tools/fusion-addin/tests/test_rules.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "RWFPostCheck"))

import dumpparse  # noqa: E402
import rules  # noqa: E402

FIX = HERE / "fixtures"
PROFILE = json.loads((HERE.parent / "RWFPostCheck" / "shop_profile.json").read_text())

failures = 0


def expect(label: str, got, want) -> None:
    global failures
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (want {want!r})"))
    if not ok:
        failures += 1


def as_op(path: Path, notes: str = "") -> dict:
    d = dumpparse.parse(path)
    return {"name": d["name"], "params": d["params"], "contours": d["contours"], "notes": notes}


print("\n== parser ==")
small = as_op(FIX / "op-small-holes.txt")
other = as_op(FIX / "op-other-holes-sketch-selected.txt")
squares = as_op(FIX / "op-squares-center.txt")
setup = dumpparse.parse(FIX / "setup.txt")
tool = dumpparse.parse(FIX / "tool-ti65-steel-125.txt")

# chains are contours; a circle is 2 edges and a square 5, so edges would lie
expect("Small Holes chains", len(small["contours"]), 1)
expect("Other Holes chains", len(other["contours"]), 4)
expect("Squares chains", len(squares["contours"]), 3)
expect("Squares edges in chain 1", len(squares["contours"][0].geometry), 5)
expect("Small Holes from body", small["contours"][0].from_body, True)
expect("Other Holes inputGeometry reads as sketch", other["contours"][0].from_body, False)
expect("Squares closed", [c.is_open for c in squares["contours"]], [False, False, False])
expect("kerf parsed (cm)", round(tool["params"]["tool_kerfWidth"], 4), 0.14)
expect("feed parsed", small["params"]["tool_feedCutting"], 2200.0)
expect("programName stays a string", setup["params"]["job_programName"], "1001")

print("\n== tool ==")
f = rules.check_tool({"name": tool["name"], "params": tool["params"]}, PROFILE)
expect("clean", [str(x) for x in f], [])

print("\n== setup ==")
f = rules.check_setup({"name": setup["name"], "params": setup["params"]}, PROFILE)
expect("one finding", len(f), 1)
expect("placeholder program name only reports - posting sets it",
       (f[0].severity, f[0].param), (rules.REPORT, "job_programName"))
expect("this setup has a model", setup["params"]["job_model"], "BRepBody")

# A setup with no model is the condition that actually reverses hole direction.
no_model = {"name": "Setup", "params": dict(setup["params"], job_model="Empty")}
f = rules.check_setup(no_model, PROFILE)
expect("missing model blocks", [x.param for x in rules.blocking(f)], ["job_model"])

print("\n== Small Holes (known good) ==")
f = rules.check_operation(small, PROFILE)
expect("clean", [str(x) for x in f], [])

print("\n== Other Holes ==")
# inputGeometry reads SketchCircle on all four chains, but these were picked
# off the body - the sketch circles and the hole edges are coincident, so the
# field cannot tell the two apart. The operation cuts CCW and its posted gcode
# is verified (path diameters 0.1324/0.1948/0.2573/0.3199). No rule fires on
# contour source; it is kept here as the case that proved the rule unusable.
f = rules.check_operation(other, PROFILE)
expect("clean - contour source is not judged", [str(x) for x in f], [])

print("\n== Squares Center (deliberate exception) ==")
f = rules.check_operation(squares, PROFILE)
expect("nothing blocks", rules.blocking(f), [])
expect("one report", len(f), 1)
expect("it is the comp side", f[0].param, "compensation")

f_noted = rules.check_operation(
    as_op(FIX / "op-squares-center.txt", notes="Center comp deliberate - kerf measurement, runbook 7"),
    PROFILE)
expect("a note on the operation silences it", f_noted, [])

print("\n== fresh op from the 'Plasma - Normal' template ==")
# Exported 2026-10-22 straight after creating an operation from the template.
# The template's tool snapshot is correct (kerf 1.4, Left / In computer) but
# picking a tool resets the preset to Default, so the op lands on 1000 mm/min
# instead of the 2200 the '1/8 Steel' preset carries. Set the preset LAST.
fresh = as_op(FIX / "op-template-fresh.txt")
f = rules.check_operation(fresh, PROFILE)
expect("name parsed from header", fresh["name"], "2D Profile7 (2)")
expect("two blocking findings", len(rules.blocking(f)), 2)
expect("empty contours caught", any(x.param == "contours" for x in f), True)
expect("Default preset caught by feed", any(x.param == "tool_feedCutting" for x in f), True)
expect("template's kerf is fine", any(x.param == "kerfWidth" for x in f), False)
expect("template's comp is fine", any(x.param == "compensation" for x in f), False)

print("\n== same template after the preset fix ==")
# Exported 2026-10-22 after setting the template to default to the '1/8 Steel'
# preset and re-creating the operation. Everything the template controls is now
# correct; the only finding left is the empty contour list, which is just what
# an operation with nothing selected yet should produce.
fixed = as_op(FIX / "op-template-fixed.txt")
f = rules.check_operation(fixed, PROFILE)
expect("feed now comes from the preset", fixed["params"]["tool_feedCutting"], 2200.0)
expect("only the empty selection remains", [x.param for x in f], ["contours"])

print("\n== whole job ==")
all_f = rules.check_job({"name": setup["name"], "params": setup["params"]},
                        [small, other, squares],
                        [{"name": tool["name"], "params": tool["params"]}],
                        PROFILE)
expect("nothing blocks - this setup is good to post", rules.blocking(all_f), [])
expect("two reports", sorted({x.param for x in all_f if x.severity == rules.REPORT}),
       ["compensation", "job_programName"])

print("\n" + ("-" * 60))
print("FAILURES:" if failures else "all assertions passed", failures or "")
sys.exit(1 if failures else 0)
