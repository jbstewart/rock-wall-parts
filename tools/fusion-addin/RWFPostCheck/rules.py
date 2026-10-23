"""Shop rules for ArcDroid plasma CAM, checked against Fusion CAM parameters.

Pure Python on purpose: no `adsk` imports anywhere in this file. The Fusion
add-in pulls parameters into plain dicts and calls in here, which means the
rules can be unit-tested headlessly against Export Parameters dumps instead of
only ever running inside Fusion where nothing can be asserted.

Every rule here exists because the mistake actually happened. See the repo
convention in AGENTS.md: every discovered bug becomes a permanent check.

UNITS: the Fusion API reports lengths in CENTIMETRES regardless of document
units, feeds in mm/min and angles in degrees. 0.14 is 1.4 mm. The shop profile
is stored in those same units so nothing has to convert at check time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BLOCK = "BLOCK"
REPORT = "REPORT"

# Geometry classes that mean "selected from a solid body". Anything starting
# with "Sketch" means the contour was picked off a sketch curve instead.
BODY_GEOMETRY = ("BRepEdge",)


@dataclass(frozen=True)
class Finding:
    severity: str          # BLOCK or REPORT
    where: str             # setup / operation / tool name
    param: str
    actual: object
    expected: object
    message: str

    def __str__(self) -> str:
        return f"{self.severity:6} {self.where:<18} {self.param:<22} {self.message}"


@dataclass
class Chain:
    """One contour selection chain. A chain is one contour; a chain may hold
    several edges (a circle comes back as two BRepEdges, a square as four or
    five). Count chains, never edges."""

    is_open: bool = False
    geometry: list[str] = field(default_factory=list)

    @property
    def from_body(self) -> bool:
        return bool(self.geometry) and all(g in BODY_GEOMETRY for g in self.geometry)

    @property
    def geometry_kinds(self) -> str:
        return ", ".join(sorted(set(self.geometry))) or "(empty)"


def _close(a: float, b: float, tol: float) -> bool:
    return abs(float(a) - float(b)) <= tol


def _get(params: dict, name: str, default=None):
    return params.get(name, default)


# --------------------------------------------------------------------------
# tool
# --------------------------------------------------------------------------

def check_tool(tool: dict, profile: dict) -> list[Finding]:
    want = profile["tool"]
    tol = profile["tolerances"]
    p = tool["params"]
    name = tool.get("name", "tool")
    out: list[Finding] = []

    kerf = _get(p, "tool_kerfWidth")
    if kerf is None:
        out.append(Finding(BLOCK, name, "tool_kerfWidth", None, want["tool_kerfWidth"],
                           "tool has no kerf width at all"))
    elif not _close(kerf, want["tool_kerfWidth"], tol["length_cm"]):
        out.append(Finding(BLOCK, name, "tool_kerfWidth", f"{kerf*10:.2f} mm",
                           f"{want['tool_kerfWidth']*10:.2f} mm",
                           "wrong kerf on the tool - a stale tool copy or a template snapshot"))

    ttype = _get(p, "tool_type")
    if ttype != want["tool_type"]:
        out.append(Finding(BLOCK, name, "tool_type", ttype, want["tool_type"],
                           "this is not a plasma cutter tool"))

    desc = _get(p, "tool_description", "")
    if desc != want["description"]:
        out.append(Finding(REPORT, name, "tool_description", desc, want["description"],
                           "not the shop's standard tool - deliberate?"))

    return out


# --------------------------------------------------------------------------
# setup
# --------------------------------------------------------------------------

def check_setup(setup: dict, profile: dict) -> list[Finding]:
    want = profile["setup"]
    p = setup["params"]
    name = setup.get("name", "Setup")
    out: list[Finding] = []

    jt = _get(p, "job_type")
    if jt != want["job_type"]:
        out.append(Finding(BLOCK, name, "job_type", jt, want["job_type"],
                           "setup is not a Cutting (jet) setup"))

    sm = _get(p, "job_stockMode")
    if sm != want["job_stockMode"]:
        detail = ("relative size box pads the stock past the blank"
                  if sm == "default" else "stock mode is not a fixed box")
        out.append(Finding(BLOCK, name, "job_stockMode", sm, want["job_stockMode"], detail))

    om = _get(p, "wcs_origin_mode")
    if om != want["wcs_origin_mode"]:
        out.append(Finding(BLOCK, name, "wcs_origin_mode", om, want["wcs_origin_mode"],
                           "origin is not the model origin - datum will not match the blank corner"))

    model = _get(p, "job_model", "")
    if not model or str(model).strip() in ("Empty", ""):
        out.append(Finding(BLOCK, name, "job_model", model or "Empty", "a body",
                           "setup has no model - with nothing to resolve against, Fusion "
                           "treats every closed contour as an outer profile and holes cut "
                           "the wrong way round"))

    # Reports, never blocks: posting SETS this from the document name, so
    # blocking here would stop the tool reaching the line that fixes it.
    pn = _get(p, "job_programName", "")
    pn = "" if pn is None else str(pn).strip()
    doc = setup.get("document_name")
    if pn in [str(x) for x in want["forbidden_program_names"]]:
        out.append(Finding(REPORT, name, "job_programName", pn or "(empty)",
                           doc or "the document name",
                           "still Fusion's placeholder - posting will set it from the "
                           "document name"))
    elif doc and pn != doc:
        out.append(Finding(REPORT, name, "job_programName", pn, doc,
                           "does not match the document name - posting will overwrite it"))

    return out


# --------------------------------------------------------------------------
# operation
# --------------------------------------------------------------------------

def check_operation(op: dict, profile: dict) -> list[Finding]:
    want = profile["operation"]
    tol = profile["tolerances"]
    p = op["params"]
    name = op.get("name", "operation")
    chains: list[Chain] = op.get("contours", [])
    notes = (op.get("notes") or "").strip()
    out: list[Finding] = []

    # --- contour selection -------------------------------------------------
    # Only the count is checked. There is NO rule on where a contour was picked
    # from, deliberately: inputGeometry reported SketchCircle for an operation
    # whose chains were picked off the body, and with the sketch circles and
    # the body's hole edges coincident there is no way to tell a sketch pick
    # from a body pick that resolved to the sketch underneath. A check that
    # cannot distinguish the two would fire on correct operations forever.
    #
    # The condition that actually reverses hole direction is a setup with no
    # model at all, and that is unambiguous - see job_model in check_setup.
    if not chains:
        out.append(Finding(BLOCK, name, "contours", 0, ">= 1",
                           "operation has no contours selected"))

    # --- kerf and feed -----------------------------------------------------
    kerf = _get(p, "kerfWidth")
    if kerf is not None and not _close(kerf, want["kerfWidth"], tol["length_cm"]):
        out.append(Finding(BLOCK, name, "kerfWidth", f"{kerf*10:.2f} mm",
                           f"{want['kerfWidth']*10:.2f} mm", "operation is cutting to the wrong kerf"))

    feed = _get(p, "tool_feedCutting")
    if feed is not None and not _close(feed, want["tool_feedCutting"], tol["feed_mmpm"]):
        hint = " - looks like the Default preset" if _close(feed, 1000.0, tol["feed_mmpm"]) else ""
        out.append(Finding(BLOCK, name, "tool_feedCutting", f"{feed:.0f} mm/min",
                           f"{want['tool_feedCutting']:.0f} mm/min", f"wrong cutting feed{hint}"))

    # --- compensation ------------------------------------------------------
    comp = _get(p, "compensation")
    any_closed = any(not ch.is_open for ch in chains)
    if comp == "center":
        # Legal and sometimes deliberate: cutting ON the line makes
        # kerf = (H - S) / 2 cancel the drawn size, which is how the squares
        # coupon measures kerf. Normal on open contours. Report, never block -
        # a validator that cries wolf on a real choice gets ignored.
        if any_closed and not notes:
            out.append(Finding(REPORT, name, "compensation", comp, want["compensation"],
                               "Center comp on a CLOSED contour - deliberate? add a note on the "
                               "operation to silence this"))
    elif comp != want["compensation"]:
        out.append(Finding(BLOCK, name, "compensation", comp, want["compensation"],
                           "wrong compensation side"))

    # compensationType is absent from the dialog entirely when comp is Center,
    # so only check it when it is actually present.
    ctype = _get(p, "compensationType")
    if comp != "center" and ctype is not None and ctype != want["compensationType"]:
        out.append(Finding(BLOCK, name, "compensationType", ctype, want["compensationType"],
                           "compensation must be applied in computer, not in control"))

    # --- leads and piercing ------------------------------------------------
    mode = _get(p, "cuttingMode")
    if mode != want["cuttingMode"]:
        out.append(Finding(REPORT, name, "cuttingMode", mode, want["cuttingMode"],
                           "not a through-auto cut"))

    if mode != "etch":
        if _get(p, "doLeadIn") is False:
            out.append(Finding(BLOCK, name, "doLeadIn", False, True,
                               "lead-in off puts the pierce crater on the finished edge"))
        dist = _get(p, "entry_distance")
        if dist is not None and dist < want["entry_distance_min"] - tol["length_cm"]:
            out.append(Finding(BLOCK, name, "entry_distance", f"{dist*10:.3f} mm",
                               f">= {want['entry_distance_min']*10:.3f} mm", "lead-in too short"))
        rad = _get(p, "entry_radius")
        if rad is not None and not _close(rad, want["entry_radius"], tol["length_cm"]):
            out.append(Finding(REPORT, name, "entry_radius", f"{rad*10:.3f} mm", "0",
                               "shop recipe is a linear perpendicular lead-in, radius 0"))
        sweep = _get(p, "entry_sweep")
        if sweep is not None and not _close(sweep, want["entry_sweep"], tol["angle_deg"]):
            out.append(Finding(REPORT, name, "entry_sweep", f"{sweep:g} deg",
                               f"{want['entry_sweep']:g} deg", "lead-in is not perpendicular"))

    pc = _get(p, "pierceClearance")
    if pc is not None:
        ok = any(_close(pc, a, tol["length_cm"]) for a in want["pierceClearance_allowed"])
        if not ok:
            allowed = " or ".join(f"{a*10:.2f} mm" for a in want["pierceClearance_allowed"])
            out.append(Finding(BLOCK, name, "pierceClearance", f"{pc*10:.2f} mm", allowed,
                               "pierce clearance is not a shop value - too big silently DROPS "
                               "small contours, too small craters the edge"))

    # --- misc --------------------------------------------------------------
    if _get(p, "group_tabs") is True:
        out.append(Finding(BLOCK, name, "group_tabs", True, False,
                           "tabs on a plasma job leave stubs to grind"))

    qc = _get(p, "machineQualityControl")
    if qc is not None and qc != want["machineQualityControl"]:
        out.append(Finding(REPORT, name, "machineQualityControl", qc, want["machineQualityControl"],
                           "ArcDroid runs on feeds, not quality numbers"))

    return out


# --------------------------------------------------------------------------
# whole job
# --------------------------------------------------------------------------

def check_job(setup: dict, operations: list[dict], tools: list[dict], profile: dict) -> list[Finding]:
    """Check a whole setup. `operations` must come from Setup.allOperations so
    that operations buried in folders and patterns are included - that is the
    count the setup sheet cannot report, and the reason this runs in Fusion
    rather than against the posted file."""
    out = list(check_setup(setup, profile))
    for t in tools:
        out.extend(check_tool(t, profile))
    for op in operations:
        out.extend(check_operation(op, profile))
    return out


def blocking(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == BLOCK]


def format_report(findings: list[Finding], setup_name: str, op_names: list[str]) -> str:
    lines = [f"Setup: {setup_name}",
             f"Operations ({len(op_names)}): " + ", ".join(op_names) or "(none)",
             ""]
    blocks = blocking(findings)
    reports = [f for f in findings if f.severity == REPORT]
    if blocks:
        lines.append(f"{len(blocks)} BLOCKING:")
        lines += [f"  {f}" for f in blocks]
        lines.append("")
    if reports:
        lines.append(f"{len(reports)} to look at:")
        lines += [f"  {f}" for f in reports]
        lines.append("")
    if not findings:
        lines.append("All shop rules pass.")
    lines += ["", "NOT checked by this tool:",
              "  - whether the contours selected are the ones the customer wanted",
              "  - whether the controller is dialled to the setup sheet",
              "  - consumable condition, clamping, material flatness"]
    return "\n".join(lines)
