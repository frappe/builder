---
description: create or change an editor plugin, including a panel, toolbar button, block right-click action, property section, or settings page; read before authoring, and again on each continuation turn
---
# Editor plugins

The code is ONE plain JavaScript ES module with no build step:
- `export default { install(app, context) { ...register items... } }`
- Import only by these bare names: "vue", "builder", "frappe-ui", and "builder/internal/<path>" for any other editor module. No other packages, no relative paths, no URLs.
- Vue is the runtime-only build: write components as objects with `setup()` returning a render function built with `h()`. No template strings, no JSX, no TypeScript, no .vue files.

Make it look like the rest of the editor, in light and in dark mode:
- Draw every control with an existing component, never your own h("input"), h("button"), h("select") or h("textarea").
- The editor's own components come first, so the plugin feels like the editor: the controls its property panel uses (builder/internal/components/Controls/ColorInput.vue, Input.vue, FontInput.vue, OptionToggle.vue, RangeInput.vue, Autocomplete.vue, GradientEditor.vue, ImageUploader.vue and more), and any other component, store or helper. Call read_editor_source to find one and read its props before you import it as "builder/internal/<path>". These are the editor's internals, so read before you guess.
- frappe-ui covers the rest: Button {label, variant: "solid"|"subtle"|"ghost", iconLeft: "lucide-<name>", loading, disabled, onClick}; FormControl {type: "text"|"password"|"number"|"textarea"|"select"|"checkbox", label, description, placeholder, options (for select), modelValue, "onUpdate:modelValue"}; Alert {title, description}; ErrorMessage {message}; Badge {label, theme}; LoadingIndicator; Tooltip {text}.
- Color only with the editor's theme classes, which switch with dark mode, and give every text element one: text-ink-gray-9 for titles, text-ink-gray-7 for text, text-ink-gray-5 for hints; bg-surface-gray-1/2 and border-outline-gray-2 for boxes. Never a hex or rgb color, an inline color or background, or plain Tailwind colors (text-gray-900, bg-white, text-black): they stay the same in dark mode, and inherited text is dark there.
- Lay out with flex, flex-col, items-center, justify-between, gap-1/2/3, p-3, px-3, py-2, w-full, truncate, rounded-4, and type with text-base (panel title), text-sm, text-p-sm (sentences), text-xs, font-medium. Other Tailwind classes may not exist at runtime.
- A panel looks like: h("div", {class: "flex flex-col gap-3 p-3"}, [h("div", {class: "text-base font-medium text-ink-gray-9"}, "Title"), h("p", {class: "text-p-sm text-ink-gray-7"}, "What it does."), h(FormControl, {label: "Name", modelValue: name.value, "onUpdate:modelValue": (value) => (name.value = value)}), h(Button, {variant: "solid", label: "Save", onClick: save})])
- The editor test-renders your components in dark mode and sends back inline colors, unreadable text and hand-drawn controls for you to fix.

When the plugin changes the page, the change must look the same once published:
- Change blocks through the Block API (setStyle, setAttribute), so it saves with the page. CSS a block needs beyond its own styles (@keyframes, media queries) goes into a Builder Client Script of script_type "CSS" attached to the page, never a <style> in the editor.
- The page publishes its root block as <body>, sized by its content, while the canvas draws it at the frame's height. A background meant to fill the screen needs minHeight "100vh" on the root block (block.isRoot()).
- Page CSS already on the page loads after block styles and wins a tie, so check pageStore.activePageScripts for rules on the same block or property before you rely on yours.

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
`context`: name, label, state.get()/state.set(values)/state.unset(key) (stored per user), setOpenHandler(fn): set it so the Open button shows the plugin, e.g. `() => (useBuilderStore().leftPanelActiveTab = "<tab name>")`.
