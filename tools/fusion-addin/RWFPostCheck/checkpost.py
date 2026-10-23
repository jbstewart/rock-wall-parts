"""All the work behind the Check & Post button. See RWFPostCheck.py for the shim.

This module holds everything that changes. RWFPostCheck.py reloads it before
every run, so edits here take effect on the next click - no Stop/Run, no
restarting Fusion. Keep new code in here, not in the shim.

It replaces right-click -> Post Process rather than adding a step you have to
remember, because there is no post event in the Fusion API: nothing can fire
automatically when you post, so the check has to BE the post.

What it does, in order:
  1. walks Setup.allOperations - including operations inside folders and
     patterns, which is the count a setup sheet cannot report, and the whole
     reason this runs here instead of against the posted file
  2. checks every operation, the tool and the setup against shop_profile.json
  3. stops dead on any blocking finding, with the operation still editable
  4. on pass: sets the program name from the document name, posts the SETUP
     (never a selected operation), then posts the setup sheet

All judgement lives in rules.py, which has no Fusion imports and is tested
headlessly against real Export Parameters dumps. This file only moves data.
"""

import json
import os
import re
import sys

import adsk.cam
import adsk.core
import adsk.fusion

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import rules  # noqa: E402


def _here(*parts):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), *parts)


def _repo_root():
    # .../<repo>/tools/fusion-addin/RWFPostCheck/this_file.py
    return os.path.abspath(_here("..", "..", ".."))


def _version():
    """Read the manifest so there is one source of truth for the version, and
    show it in the dialog: an add-in running code you edited ten minutes ago is
    the hardest failure here to spot by eye."""
    try:
        with open(_here("RWFPostCheck.manifest")) as fh:
            return json.load(fh).get("version", "?")
    except Exception:
        return "?"


def _profile():
    with open(_here("shop_profile.json")) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# reading parameters out of the live API into the plain dicts rules.py wants
# --------------------------------------------------------------------------

def _scalar(cam_params, name):
    """One parameter's value, or None if the parameter is not present.

    Absent is not the same as wrong: compensationType disappears from the
    dialog entirely when compensation is Center, so rules.py skips checks
    whose parameter came back None rather than failing on a missing key."""
    try:
        p = cam_params.itemByName(name)
    except Exception:
        return None
    if p is None:
        return None
    try:
        return p.value.value
    except Exception:
        return None


def _params_dict(cam_params, names):
    return {n: _scalar(cam_params, n) for n in names}


SETUP_PARAMS = ["job_type", "job_stockMode", "wcs_origin_mode", "job_programName", "job_model",
                "job_programComment", "job_stockFixedX", "job_stockFixedY", "job_stockFixedZ"]

OP_PARAMS = ["compensation", "compensationType", "kerfWidth", "tool_feedCutting",
             "pierceClearance", "doLeadIn", "doLeadOut", "entry_distance", "entry_radius",
             "entry_sweep", "cuttingMode", "group_tabs", "machineQualityControl"]

TOOL_PARAMS = ["tool_kerfWidth", "tool_type", "tool_description", "tool_nozzleDiameter"]


def _chains(op):
    """Contour chains for an operation. One chain is one contour; a chain holds
    several edges (a circle is two BRepEdges, a square four or five), so chains
    are counted and edges are only inspected for where they came from."""
    out = []
    try:
        p = op.parameters.itemByName("contours")
        selections = p.value.getCurveSelections()
    except Exception:
        return out
    for i in range(selections.count):
        sel = selections.item(i)
        chain = rules.Chain()
        chain.is_open = bool(getattr(sel, "isOpen", False))
        try:
            for ent in sel.inputGeometry:
                # 'adsk::fusion::BRepEdge' -> 'BRepEdge'
                chain.geometry.append(str(ent.objectType).split("::")[-1])
        except Exception:
            pass
        out.append(chain)
    return out


def _model_state(setup):
    """"BRepBody" / "Empty", matching what Export Parameters prints.

    job_model is a CadObjectParameterValue - a collection of entities, not a
    scalar - so the generic reader above gets nothing out of it and a setup
    with a perfectly good body reads as empty. Setup.models is the direct
    property and is what to trust."""
    try:
        return "BRepBody" if setup.models.count > 0 else "Empty"
    except Exception:
        return "unknown"


def collect(setup, document_name):
    """Everything the rules need, as plain data."""
    params = _params_dict(setup.parameters, SETUP_PARAMS)
    params["job_model"] = _model_state(setup)
    setup_d = {"name": setup.name,
               "params": params,
               "document_name": document_name}

    ops, tools, seen = [], [], set()
    for op in setup.allOperations:
        ops.append({"name": op.name,
                    "params": _params_dict(op.parameters, OP_PARAMS),
                    "contours": _chains(op),
                    "notes": getattr(op, "notes", "") or ""})
        try:
            tool = op.tool
        except Exception:
            tool = None
        if tool is not None:
            key = _scalar(tool.parameters, "tool_description")
            if key not in seen:
                seen.add(key)
                tools.append({"name": key or "tool",
                              "params": _params_dict(tool.parameters, TOOL_PARAMS)})
    return setup_d, ops, tools


# --------------------------------------------------------------------------
# staleness - a check on settings is worthless against an out-of-date toolpath
# --------------------------------------------------------------------------

def stale_operations(setup):
    bad = []
    for op in setup.allOperations:
        if getattr(op, "isSuppressed", False):
            continue
        if not getattr(op, "hasToolpath", True):
            bad.append(f"{op.name}: no toolpath - Generate first")
        elif getattr(op, "isValid", True) is False:
            bad.append(f"{op.name}: toolpath is out of date - Generate first")
        elif getattr(op, "hasError", False):
            bad.append(f"{op.name}: {getattr(op, 'error', 'operation has an error')}")
    return bad


# --------------------------------------------------------------------------
# posting
# --------------------------------------------------------------------------

def _snapshot(folder):
    """{filename: (mtime, size)} for everything in the output folder."""
    out = {}
    try:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                st = os.stat(full)
                out[name] = (st.st_mtime, st.st_size)
    except Exception:
        pass
    return out


def _changed_since(folder, before):
    """Files this post actually created or rewrote, newest first.

    Posting is reported as succeeding whether or not a file appears, so the
    only honest confirmation is to look at the folder."""
    after = _snapshot(folder)
    changed = [n for n, v in after.items() if before.get(n) != v]
    changed.sort(key=lambda n: after[n][0], reverse=True)
    return [f"{n}  ({after[n][1]:,} bytes)" for n in changed]


def _part_and_rev(document_name):
    """Split 'arcdroid-profile-coupon-revA' into ('arcdroid-profile-coupon', 'A').

    These feed the post's partName/partRev PROPERTIES, which is how the
    'PART ... REV A' and 'POSTED' header lines get written. Posting through the
    UI dialog carries whatever you last typed there; an API post carries
    nothing, so the header block is silently skipped unless we pass them."""
    m = re.match(r"^(.*?)-rev([A-Za-z]+)$", document_name)
    if m:
        return m.group(1), m.group(2).upper()
    return document_name, ""


def post(cam, setup, program_name, profile, ui):
    paths = profile["paths"]
    out_dir = os.path.expanduser(paths["output_folder"])
    gcode_post = os.path.join(_repo_root(), paths["gcode_post"])
    sheet_post = os.path.join(_repo_root(), paths["sheet_post"])

    for label, path in (("post", gcode_post), ("setup sheet post", sheet_post)):
        if not os.path.isfile(path):
            ui.messageBox(f"Cannot find the {label}:\n{path}")
            return False
    if not os.path.isdir(out_dir):
        ui.messageBox(f"Output folder does not exist:\n{out_dir}")
        return False

    part_name, part_rev = _part_and_rev(program_name)
    units = adsk.cam.PostOutputUnitOptions.MillimetersOutput
    written = []
    for label, path in (("program", gcode_post), ("setup sheet", sheet_post)):
        before = _snapshot(out_dir)
        pin = adsk.cam.PostProcessInput.create(program_name, path, out_dir, units)
        pin.isOpenInEditor = False
        try:
            props = adsk.core.NamedValues.create()
            props.add("partName", adsk.core.ValueInput.createByString(part_name))
            props.add("partRev", adsk.core.ValueInput.createByString(part_rev))
            pin.postProperties = props
        except Exception:
            pass  # header comments only; never worth failing a post over
        # The SETUP, never a selected operation - Fusion posts only what it is
        # handed, and posting a selection is how a 3-op program became a 1-op
        # program twice in one evening.
        try:
            cam.postProcess(setup, pin)
        except Exception as exc:
            ui.messageBox(f"The {label} post failed:\n\n{exc}\n\n"
                          f"post: {path}")
            return False
        touched = _changed_since(out_dir, before)
        if not touched:
            # A post that silently writes nothing is the worst outcome: you
            # walk out to the shop with the PREVIOUS file and no reason to
            # doubt it. Never report success for it.
            ui.messageBox(f"The {label} post reported no error but wrote nothing to\n"
                          f"{out_dir}\n\npost: {path}")
            return False
        failed = [f for f in touched if f.endswith(".failed")]
        if failed:
            ui.messageBox(f"The {label} post failed - it left:\n  " + "\n  ".join(failed))
            return False
        written.extend(touched)

    ui.messageBox("Posted to " + out_dir + "\n\n  " + "\n  ".join(written))
    return True


# --------------------------------------------------------------------------
# command
# --------------------------------------------------------------------------

def choose_setup(cam, ui):
    if cam.setups.count == 0:
        ui.messageBox("This document has no CAM setups.")
        return None
    if cam.setups.count == 1:
        return cam.setups.item(0)
    for i in range(ui.activeSelections.count):
        ent = ui.activeSelections.item(i).entity
        if isinstance(ent, adsk.cam.Setup):
            return ent
    ui.messageBox(f"This document has {cam.setups.count} setups.\n\n"
                  "Select the one you want in the browser, then run this again.")
    return None


def run_check(app, ui):
    product = app.activeProduct
    if not isinstance(product, adsk.cam.CAM):
        ui.messageBox("Switch to the Manufacture workspace first.")
        return
    cam = product
    setup = choose_setup(cam, ui)
    if setup is None:
        return

    doc_name = os.path.splitext(app.activeDocument.name)[0]
    profile = _profile()

    stale = stale_operations(setup)
    if stale:
        ui.messageBox("Toolpaths are not up to date, so there is nothing "
                      "trustworthy to check:\n\n  " + "\n  ".join(stale))
        return

    setup_d, ops, tools = collect(setup, doc_name)
    findings = rules.check_job(setup_d, ops, tools, profile)
    report = rules.format_report(findings, setup.name, [o["name"] for o in ops])

    title = f"RWF Check & Post v{_version()}"
    if rules.blocking(findings):
        ui.messageBox(report, f"{title} - not posted, fix these first")
        return

    out_dir = os.path.expanduser(profile["paths"]["output_folder"])
    answer = ui.messageBox(
        report + "\n\n"
        f"Post setup '{setup.name}' ({len(ops)} operations)\n"
        f"as  {doc_name}.gcode  + setup sheet\n"
        f"to  {out_dir} ?",
        f"{title} - shop rules pass",
        adsk.core.MessageBoxButtonTypes.YesNoButtonType,
        adsk.core.MessageBoxIconTypes.QuestionIconType)
    if answer != adsk.core.DialogResults.DialogYes:
        return

    # Name the program after the document so it is never typed, and so the
    # posted file inherits the naming and the rev letter already on the doc.
    try:
        setup.parameters.itemByName("job_programName").expression = "'{}'".format(doc_name)
    except Exception:
        pass

    post(cam, setup, doc_name, profile, ui)
