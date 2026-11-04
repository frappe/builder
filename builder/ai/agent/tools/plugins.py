"""Editor plugins Bob writes for the user: a panel, a toolbar button, a block
menu action. They live in the editor, and what they make lands on the page.

`write_plugin` installs the plugin for everyone who edits the site
(builder.plugins.bob), then has the open editor load it and report back: the
error, or what the plugin put on screen. So Bob fixes its own plugin in the same
turn, the way it re-reads a page after editing it.
"""

import re
from collections import defaultdict
from pathlib import Path

import frappe

from builder.ai.agent.registry import Tool
from builder.plugins import bob
from builder.plugins.access import INSTALLATION_DOCTYPE, find_installation, is_plugin_manager

# long enough for a cold editor to fetch and import the module, short enough to give up
# on a closed tab before the user wonders what Bob is doing
LOAD_REPORT_TIMEOUT = 15

# what hostModules.mjs leaves out of the import map: tests, type files and the app's own entry
NOT_A_MODULE = re.compile(r"(\.test\.ts|\.d\.ts)$")
MAX_SOURCE_CHARS = 15_000

SURFACES = {
	"leftPanelTabs": "left bar tab",
	"toolbarItems": "toolbar item",
	"blockContextMenuOptions": "block right-click menu item",
	"propertySections": "property panel section",
	"settingsItems": "settings page",
}


def run_write_plugin(ctx, args: dict) -> str:
	if not is_plugin_manager():
		return (
			"DECLINED: only a System Manager or a Website Manager can add plugins, so nothing was "
			"saved. Tell the user in one plain sentence."
		)
	if missing := ctx.require_skill("editor-plugin"):
		return missing
	code = args.get("code") or ""
	if error := bob.syntax_error(code):
		return f"FAILED: main.js does not parse, so nothing was saved. Fix it and call write_plugin again.\n{error}"

	doc = bob.save_plugin(
		# read_plugin lists the full id, and models pass it back as the name
		(args.get("name") or "").strip().removeprefix(f"{bob.PUBLISHER}/"),
		(args.get("label") or "").strip(),
		(args.get("description") or "").strip(),
		code,
		args.get("icon"),
	)
	if doc.plugin not in ctx.plugins_written:
		ctx.plugins_written.append(doc.plugin)
	if not ctx.page_id:
		return "Installed. It loads the next time each user opens the editor."
	if not doc.enabled:
		return "Saved, but the plugin is turned off on this site. Tell the user to turn it on in the Plugins panel."
	return load_in_editor(ctx, doc)


def load_in_editor(ctx, doc) -> str:
	"""The editor loads the plugin in its own request, which must see the row, so this
	commits early. Nothing after the commit may raise: the loop's savepoint is gone."""
	from builder.ai.agent.loop import CancelledError

	token = frappe.generate_hash(length=16)
	frappe.db.commit()  # nosemgrep
	try:
		ctx.emit("tool_batch", operations=[load_op(doc, token)])
		report = wait_for_report(ctx, token)
	except CancelledError:
		raise
	except Exception as e:
		return f"Installed, but the editor could not be asked to load it ({e})."
	return describe_report(doc, report)


def load_op(doc, token: str) -> dict:
	return {
		"tool_name": "load_plugin",
		"args": {
			"plugin": doc.plugin,
			"label": doc.label,
			"version": doc.version,
			"entry_url": doc.entry_url,
			"token": token,
		},
	}


def wait_for_report(ctx, token: str) -> dict | None:
	waited = 0.0
	while waited < LOAD_REPORT_TIMEOUT:
		if report := bob.get_load_report(ctx.user, token):
			return report
		ctx.interruptible_sleep(0.25)
		waited += 0.25
	return None


def describe_report(doc, report: dict | None) -> str:
	if report is None:
		return (
			"Installed, but the editor did not report back, so it is not confirmed working. "
			"It loads the next time the user opens the editor."
		)
	if report.get("disabled"):
		return "Saved, but this user turned plugins off in this browser, so it is not running. Tell them."
	if report.get("unchanged"):
		return "The code is the same as the version already running in the editor, so nothing changed."
	if report.get("error"):
		return (
			"FAILED: installed, but it did not load in the editor. Fix the code and call "
			f"write_plugin again with the whole file.\n{report['error']}"
		)
	registered = report.get("registered") or []
	if problems := report.get("problems"):
		return (
			"FAILED: it loaded, but needs a fix. Fix it and call write_plugin again with the whole file.\n"
			+ "\n".join(problems)
		)
	if not registered:
		return (
			"FAILED: it loaded but registered nothing the editor shows. install() must register "
			"at least one item."
		)
	added = "; ".join(
		f'{SURFACES.get(item["surface"], item["surface"])} "{item["label"]}"' for item in registered
	)
	return (
		f"Running in this user's editor (version {doc.version}); everyone else who edits the site gets it on their next editor load. "
		f"It added: {added}. Its components rendered without errors. The chat shows a card with "
		"Open. Tell the user where to find it in a sentence; do not walk through the code."
	)


def run_read_plugin(ctx, args: dict) -> str:
	name = (args.get("name") or "").strip()
	if not name:
		return list_plugins()
	plugin = name if "/" in name else f"{bob.PUBLISHER}/{name}"
	installation = find_installation(plugin)
	if not installation:
		return f"FAILED: no plugin '{plugin}' on this site. Call read_plugin with no name to list them."
	doc = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
	if doc.source != "Bob":
		return f"{plugin} came from {doc.source}. It is a built package, so you cannot change it."
	code = bob.read_code(doc)
	return f"{plugin} ({doc.label}, version {doc.version})\n--- main.js ---\n{code or ''}"


def list_plugins() -> str:
	rows = frappe.get_all(
		INSTALLATION_DOCTYPE,
		fields=["plugin", "label", "source", "enabled"],
		order_by="modified desc",
	)
	lines = [plugin_line(row) for row in rows]
	return "\n".join(lines) or "No plugins on this site yet."


def plugin_line(row) -> str:
	off = ", turned off" if not row.enabled else ""
	return f"- {row.plugin}: {row.label} ({row.source}{off})"


WRITE_PLUGIN_DESCRIPTION = """Add a tool to the Builder editor that the user works with themselves: a left bar panel, a toolbar button, a block right-click action, a property panel section, a settings page. It usually acts on their pages, inserting blocks or restyling the selection ("an icon picker", "a duotone for my photos"). When the user wants one change made to this page, make it with the page tools instead. Call it again with the same name and the WHOLE file to change a plugin; read_plugin shows the current code.

It installs the plugin for everyone who edits this site and loads it into this user's open editor at once; the others get it on their next editor load. The result says whether it loaded, what it added, or the error to fix.

Before authoring or changing code, read_skill('editor-plugin') this turn, including on continuations. It documents the module/API, render functions, editor UI/theme, and publication requirements."""

write_plugin_tool = Tool(
	name="write_plugin",
	skill="editor-plugin",
	side="server",
	description=WRITE_PLUGIN_DESCRIPTION,
	parameters={
		"type": "object",
		"properties": {
			"name": {
				"type": "string",
				"description": 'Short id in lowercase-with-hyphens, e.g. "alt-text-audit". The same name updates the plugin.',
			},
			"label": {
				"type": "string",
				"description": 'What the user sees, e.g. "Alt text audit". Up to 80 characters.',
			},
			"description": {
				"type": "string",
				"description": "One plain sentence on what it does, up to 240 characters.",
			},
			"icon": {
				"type": "string",
				"description": 'A lucide icon name for the Plugins list, e.g. "image-off".',
			},
			"code": {"type": "string", "description": "The whole main.js module."},
		},
		"required": ["name", "label", "description", "code"],
	},
	handler=run_write_plugin,
)

read_plugin_tool = Tool(
	name="read_plugin",
	side="server",
	description=(
		"List the editor plugins on this site, or, given a name, read the code of one you wrote. "
		"Read a plugin before you change it with write_plugin."
	),
	parameters={
		"type": "object",
		"properties": {
			"name": {
				"type": "string",
				"description": 'A plugin name, e.g. "alt-text-audit". Omit to list them.',
			},
		},
	},
	handler=run_read_plugin,
)


def run_read_editor_source(ctx, args: dict) -> str:
	root = editor_source_root()
	if not root.is_dir():
		return "FAILED: the editor's source is not on this server. Use the documented imports only."
	if path := (args.get("path") or "").strip():
		return read_module(root, path)
	return list_modules(root, (args.get("search") or "").strip().lower())


def editor_source_root() -> Path:
	return Path(frappe.get_app_path("builder")).parent / "frontend" / "src"


def editor_modules(root: Path) -> list[Path]:
	main = root / "main.ts"
	return sorted(
		path
		for path in root.rglob("*")
		if path.suffix in (".ts", ".vue") and not NOT_A_MODULE.search(path.name) and path != main
	)


def import_name(path: Path, root: Path) -> str:
	"""How a plugin imports it: a .ts module drops its suffix, a .vue module keeps it."""
	return "builder/internal/" + path.relative_to(root).as_posix().removesuffix(".ts")


def list_modules(root: Path, search: str) -> str:
	"""Grouped by folder, so the whole editor fits in one answer."""
	folders = defaultdict(list)
	for path in editor_modules(root):
		if search and search not in import_name(path, root).lower():
			continue
		folders[path.parent.relative_to(root).as_posix()].append(path.name.removesuffix(".ts"))
	if not folders:
		return f"No editor module matches '{search}'."
	lines = [f"builder/internal/{folder}/: {', '.join(names)}" for folder, names in sorted(folders.items())]
	return "\n".join(lines)


def read_module(root: Path, name: str) -> str:
	relative = name.removeprefix("builder/internal/").lstrip("/")
	for candidate in (relative, f"{relative}.ts"):
		path = (root / candidate).resolve()
		if path.is_relative_to(root.resolve()) and path.is_file():
			source = path.read_text()
			cut = "\n... (truncated)" if len(source) > MAX_SOURCE_CHARS else ""
			return f"{import_name(path, root.resolve())}\n{source[:MAX_SOURCE_CHARS]}{cut}"
	return f"FAILED: no editor module '{name}'. Call read_editor_source with a search to find one."


read_editor_source_tool = Tool(
	name="read_editor_source",
	skill="editor-plugin",
	side="server",
	description=(
		"Find and read the editor's own modules, to build a plugin from them: the controls its panels use "
		"(color, font, number, toggle, autocomplete inputs), its stores, helpers and components. With no "
		"path it lists every module by folder, narrowed by `search`; with a path it returns that module's "
		"source, so you can see a component's props before you import it in a plugin."
	),
	parameters={
		"type": "object",
		"properties": {
			"search": {"type": "string", "description": 'Part of a module path, e.g. "color" or "Controls".'},
			"path": {
				"type": "string",
				"description": 'A module to read, e.g. "builder/internal/components/Controls/ColorInput.vue".',
			},
		},
	},
	handler=run_read_editor_source,
)

TOOLS = [write_plugin_tool, read_plugin_tool, read_editor_source_tool]
