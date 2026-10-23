"""Rock Wall Forge — Check & Post. Fusion add-in entry point.

Deliberately almost empty. Fusion caches the add-in module itself, so anything
living here needs a Fusion restart to pick up an edit - which is how an
afternoon gets lost staring at a rule you already deleted. All the work is in
checkpost.py and its imports, and _reload_siblings() re-imports every module in
this folder before each run. Edit those freely; they take effect next click.

Only touch this file to change the button or the panel it sits on.
"""

import importlib
import os
import sys
import traceback

import adsk.core

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import checkpost  # noqa: E402

CMD_ID = "RWFPostCheckCmd"
CMD_NAME = "Check && Post"
CMD_TOOLTIP = "Check this setup against the Rock Wall Forge shop rules, then post it."
# Fusion wants a FOLDER of PNGs (16x16, 32x32 and @2x), not an image file, and
# picks per display scale. Without it the command has no icon - and a command
# with no icon cannot be pinned to the toolbar. Regenerate with make_icons.py.
ICON_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           "resources", "CheckPost")
PANEL_ID = "CAMActionPanel"
WORKSPACE_ID = "CAMEnvironment"

_handlers = []  # Fusion garbage-collects handlers that nothing holds on to


def _reload_siblings():
    """Re-import every module that lives in this folder, deepest first.

    Named modules are not listed on purpose - a new module added later reloads
    without anyone remembering to add it here."""
    here = os.path.dirname(os.path.realpath(__file__))
    mine = []
    for name, mod in list(sys.modules.items()):
        path = getattr(mod, "__file__", None)
        if not path or name == __name__:
            continue
        if os.path.dirname(os.path.realpath(path)) == here:
            mine.append((name, mod))
    # rules/dumpparse before checkpost, so checkpost picks up fresh references
    for name, mod in sorted(mine, key=lambda kv: kv[0] == "checkpost"):
        importlib.reload(mod)


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface
        try:
            _reload_siblings()
            checkpost.run_check(app, ui)
        except Exception:
            ui.messageBox("RWF Check & Post failed:\n\n" + traceback.format_exc())


class _CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        handler = _ExecuteHandler()
        args.command.execute.add(handler)
        _handlers.append(handler)
        args.command.isAutoExecute = True  # nothing to configure, skip the dialog


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        existing = ui.commandDefinitions.itemById(CMD_ID)
        if existing:
            existing.deleteMe()
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_TOOLTIP, ICON_FOLDER)
        handler = _CreatedHandler()
        cmd_def.commandCreated.add(handler)
        _handlers.append(handler)

        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        if panel.controls.itemById(CMD_ID) is None:
            panel.controls.addCommand(cmd_def)
    except Exception:
        ui.messageBox("RWF Check & Post failed to load:\n\n" + traceback.format_exc())


def stop(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        control = panel.controls.itemById(CMD_ID)
        if control:
            control.deleteMe()
        cmd_def = ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()
    except Exception:
        ui.messageBox("RWF Check & Post failed to unload:\n\n" + traceback.format_exc())
