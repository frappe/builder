"""Editor plugins Bob writes for the user: a panel, a toolbar button, a block
menu action. They extend the editor itself, never the page.

`write_plugin` saves a draft that runs only for this user (builder.plugins.drafts),
then has the open editor load it and report back: the error, or what the plugin
put on screen. So Bob fixes its own plugin in the same turn, the way it re-reads
a page after editing it. Sharing with the team is the user's click, never Bob's.
"""

import frappe

from builder.ai.agent.registry import Tool
from builder.plugins import drafts
from builder.plugins.access import INSTALLATION_DOCTYPE, find_installation, is_plugin_manager

# long enough for a cold editor to fetch and import the module, short enough to give up
# on a closed tab before the user wonders what Bob is doing
LOAD_REPORT_TIMEOUT = 15

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
	code = args.get("code") or ""
	if error := drafts.syntax_error(code):
		return f"FAILED: main.js does not parse, so nothing was saved. Fix it and call write_plugin again.\n{error}"

	doc = drafts.save_draft(
		# read_plugin lists the full id, and models pass it back as the name
		(args.get("name") or "").strip().removeprefix(f"{drafts.PUBLISHER}/"),
		(args.get("label") or "").strip(),
		(args.get("description") or "").strip(),
		code,
		args.get("icon"),
	)
	if doc.plugin not in ctx.plugins_written:
		ctx.plugins_written.append(doc.plugin)
	if not ctx.page_id:
		return "Saved as a draft only this user runs. It loads the next time they open the editor."
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
		return f"Saved as a draft, but the editor could not be asked to load it ({e})."
	return describe_report(doc, report)


def load_op(doc, token: str) -> dict:
	return {
		"tool_name": "load_plugin",
		"args": {
			"plugin": doc.plugin,
			"label": doc.label,
			"version": doc.version,
			"entry_url": doc.entry_url_for(frappe.session.user),
			"token": token,
		},
	}


def wait_for_report(ctx, token: str) -> dict | None:
	waited = 0.0
	while waited < LOAD_REPORT_TIMEOUT:
		if report := drafts.get_load_report(ctx.user, token):
			return report
		ctx.interruptible_sleep(0.25)
		waited += 0.25
	return None


def describe_report(doc, report: dict | None) -> str:
	if report is None:
		return (
			"Saved as a draft, but the editor did not report back, so it is not confirmed working. "
			"It loads the next time the user opens the editor."
		)
	if report.get("disabled"):
		return "Saved, but this user turned plugins off in this browser, so it is not running. Tell them."
	if report.get("unchanged"):
		return "The code is the same as the version already running in the editor, so nothing changed."
	if report.get("error"):
		return (
			"FAILED: saved as a draft, but it did not load in the editor. Fix the code and call "
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
		f"Running in this user's editor (version {doc.version}), as a draft only they see. "
		f"It added: {added}. Its components rendered without errors. The chat shows a card with "
		"Open and Share. Tell the user where to find it in a sentence; do not walk through the code."
	)


def run_read_plugin(ctx, args: dict) -> str:
	name = (args.get("name") or "").strip()
	if not name:
		return list_plugins()
	plugin = name if "/" in name else f"{drafts.PUBLISHER}/{name}"
	installation = find_installation(plugin)
	if not installation:
		return f"FAILED: no plugin '{plugin}' on this site. Call read_plugin with no name to list them."
	doc = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
	if doc.source != "Bob":
		return f"{plugin} came from {doc.source}. It is a built package, so you cannot change it."
	code = drafts.read_code(doc, frappe.session.user)
	return f"{plugin} ({doc.label}, version {doc.version})\n--- main.js ---\n{code or ''}"


def list_plugins() -> str:
	rows = frappe.get_all(
		INSTALLATION_DOCTYPE,
		fields=["plugin", "label", "source", "enabled", "checksum", "draft_owner"],
		order_by="modified desc",
	)
	lines = [plugin_line(row) for row in rows if row.checksum or row.draft_owner == frappe.session.user]
	return "\n".join(lines) or "No plugins on this site yet."


def plugin_line(row) -> str:
	if row.draft_owner == frappe.session.user:
		state = "draft only this user runs" if not row.checksum else "shared, with this user's unshared draft"
	else:
		state = "shared"
	off = ", turned off" if not row.enabled else ""
	return f"- {row.plugin}: {row.label} ({row.source}, {state}{off})"


WRITE_PLUGIN_DESCRIPTION = """Add a tool to the Builder EDITOR itself for this user: a left bar panel, a toolbar button, a block right-click action, a property panel section, a settings page. Use it when the user asks for something in the editor (\"a panel that lists images without alt text\"), never for content on their page. Call it again with the same name and the WHOLE file to change a plugin; read_plugin shows the current code.

It saves a draft that runs only for this user and loads it into their open editor at once. The result says whether it loaded, what it added, or the error to fix. Sharing it with the team is the user's choice (the Share button); you cannot share.

The code is ONE plain JavaScript ES module with no build step:
- `export default { install(app, context) { ...register items... } }`
- Import only by these bare names: "vue", "builder", "frappe-ui". No other packages, no relative paths, no URLs.
- Vue is the runtime-only build: write components as objects with `setup()` returning a render function built with `h()`. No template strings, no JSX, no TypeScript, no .vue files.

Make it look like the rest of the editor, in light and in dark mode:
- Draw every control with a frappe-ui component, never your own h("input"), h("button"), h("select") or h("textarea"): Button {label, variant: "solid"|"subtle"|"ghost", iconLeft: "lucide-<name>", loading, disabled, onClick}; FormControl {type: "text"|"password"|"number"|"textarea"|"select"|"checkbox", label, description, placeholder, options (for select), modelValue, "onUpdate:modelValue"}; Alert {title, description}; ErrorMessage {message}; Badge {label, theme}; LoadingIndicator; Tooltip {text}.
- Color only with the editor's theme classes, which switch with dark mode, and give every text element one: text-ink-gray-9 for titles, text-ink-gray-7 for text, text-ink-gray-5 for hints; bg-surface-gray-1/2 and border-outline-gray-2 for boxes. Never a hex or rgb color, an inline color or background, or plain Tailwind colors (text-gray-900, bg-white, text-black): they stay the same in dark mode, and inherited text is dark there.
- Lay out with flex, flex-col, items-center, justify-between, gap-1/2/3, p-3, px-3, py-2, w-full, truncate, rounded-4, and type with text-base (panel title), text-sm, text-p-sm (sentences), text-xs, font-medium. Other Tailwind classes may not exist at runtime.
- A panel looks like: h("div", {class: "flex flex-col gap-3 p-3"}, [h("div", {class: "text-base font-medium text-ink-gray-9"}, "Title"), h("p", {class: "text-p-sm text-ink-gray-7"}, "What it does."), h(FormControl, {label: "Name", modelValue: name.value, "onUpdate:modelValue": (value) => (name.value = value)}), h(Button, {variant: "solid", label: "Save", onClick: save})])
- The editor test-renders your components in dark mode and sends back inline colors, unreadable text and hand-drawn controls for you to fix.

"builder" exports:
- Registries, each `register(item)` returning its unregister. Prefix item names with the plugin name and keep them stable across edits.
  leftPanelTabs: {name, label, icon, component}. A tab in the left bar.
  toolbarItems: {name, region: "left"|"center"|"right", component}
  blockContextMenuOptions: {name, label, action: ({block}) => void, condition?: ({block}) => boolean}
  settingsItems: {name, label, title, icon, group: "Current Page"|"Global", component}
  propertySections: {name, properties: [{component, getProps: () => ({}), searchKeyWords: "words"}]}
- lucideIcon("lucide-<name>") for every icon field, e.g. `icon: lucideIcon("lucide-image-off")`. A plain string draws nothing.
- usePageStore(): pageBlocks[0] is the root Block, activePage the Builder Page doc. useBuilderStore(): leftPanelActiveTab = a tab name opens it. useCanvasStore().
- blockController.getSelectedBlocks(), blockController.getFirstSelectedBlock()
- A Block has blockId, element, children, getTextContent(), getStyle(prop), setStyle(prop, value), getAttribute(name), setAttribute(name, value), isText(), isImage(), isContainer(), selectBlock(), getParentBlock(). Walk `children` to visit the tree.
"frappe-ui": the components above, call(method, args) and createResource for whitelisted methods with the user's own permissions, toast.success/toast.error.
`context`: name, label, state.get()/state.set(values)/state.unset(key) (stored per user), setOpenHandler(fn): set it so the Open button shows the plugin, e.g. `() => (useBuilderStore().leftPanelActiveTab = "<tab name>")`."""

write_plugin_tool = Tool(
	name="write_plugin",
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

TOOLS = [write_plugin_tool, read_plugin_tool]
