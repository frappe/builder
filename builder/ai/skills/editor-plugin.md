---
description: create, change or suggest an editor plugin (a panel, toolbar button, block right-click action, property section, or settings page); read before proposing or authoring, and again on each continuation turn
---
# Editor plugins

## What a good plugin is
A plugin is a shortcut the user reaches for while making a page: open it, put something on the page in a few seconds, carry on. Most good ones take one of these shapes:
- Insert: a grid of visual things to add (icons, photos, illustrations, shapes, patterns, embeds, the site's own records). Click or drag one and it lands on the page as ordinary blocks.
- Restyle the selection: select a block, see your own content in a range of looks, click one. Image treatments, text styles, backgrounds, borders, motion.
- Generate: a small input becomes a block: a link becomes a QR code, numbers become a chart, a photo becomes a palette.
- Check: list what needs fixing on the page and jump to each block. Build it when the user asks for a check; something fun or visual is one of the other three.

Every plugin keeps to these:
- One job, named after it: a label of a word or two, a description of one clause with no "and".
- The first screen is the product: opening it already shows results with defaults that look good (popular items, the selection in each look), with no intro paragraph, setup step or empty form before them.
- Show, then click. Each choice is a tile previewing its result, drawn on the user's own content when a block is selected. The left panel is about 300px wide, so tiles sit two or three to a row.
- Two controls at most above the tiles, such as a search box and a Shuffle. Size, color, spacing and position are what the editor's own panels change once the block is on the page, so the plugin leaves them there.
- The panel explains itself by behaving: a tile that inserts on click needs no line saying so. Its words are the tile names, plus one hint line when there is nothing to show. An item's source and license sit in the tile's tooltip, and an attribution the page owes travels with the block it inserts (its alt text or a caption).
- The result lives on the page: ordinary blocks and styles the user keeps editing in the normal panels, and that publish the same. A panel that only entertains (a spinning model, a toy) gives the user nothing to keep.
- Selection-aware. When the job needs a selection, follow it live; with none, a one-line hint ("Select an image") stands where the tiles would be.
- Undo belongs to the editor. Every Block API change is one Cmd+Z, so the plugin carries no undo, restore or history of its own.
- The smallest version that does the job well. Favorites, recents, presets, settings screens and API key fields wait until the user asks; name one or two as next steps in your reply. Use sources that need no key; when one is unavoidable, ask for it inside the panel the first time it is needed.
- Fun is speed and surprise: results appear as the user types, every click lands at once, the range is bold and varied, and a Shuffle deals a fresh set.

When the user asks what you could build, offer three ideas at most and say which you'd pick, each in one sentence on what the user does and what lands on their page. After building, the reply says where the plugin is and the one thing to try first, in a sentence or two.

## The module
A new plugin starts from this guide alone: read_plugin with no name lists the others so it gets a name of its own. You read a plugin's code only to change that plugin; how another plugin did something is no reference, this guide and the editor's source are.

The code is ONE plain JavaScript ES module with no build step:
- `export default { install(app, context) { ...register items... } }`
- Import only by these bare names: "vue", "builder", "frappe-ui", and "builder/internal/<path>" for any other editor module. No other packages, no relative paths, no URLs.
- Vue is the runtime-only build: write components as objects with `setup()` returning a render function built with `h()`. No template strings, no JSX, no TypeScript, no .vue files.

## Looks
Make it look like the rest of the editor, in light and in dark mode:
- Draw every control with an existing component, never your own h("input"), h("button"), h("select") or h("textarea"). A tile is a div with an onClick.
- The editor's own components come first, so the plugin feels like the editor: the controls its property panel uses (builder/internal/components/Controls/ColorInput.vue, Input.vue, FontInput.vue, OptionToggle.vue, RangeInput.vue, Autocomplete.vue, GradientEditor.vue, ImageUploader.vue and more), and any other component, store or helper. Call read_editor_source to find one and read its props before you import it as "builder/internal/<path>". These are the editor's internals, so read before you guess.
- frappe-ui covers the rest: Button {label, variant: "solid"|"subtle"|"ghost", iconLeft: "lucide-<name>", loading, disabled, onClick}; FormControl {type: "text"|"password"|"number"|"textarea"|"select"|"checkbox", label, description, placeholder, options (for select), modelValue, "onUpdate:modelValue"}; Alert {title, description}; ErrorMessage {message}; Badge {label, theme}; LoadingIndicator; Tooltip {text}.
- Color the plugin's own chrome only with the editor's theme classes, which switch with dark mode, and give every text element one: text-ink-gray-9 for titles, text-ink-gray-7 for text, text-ink-gray-5 for hints; bg-surface-gray-1/2 and border-outline-gray-2 for boxes. Never a hex or rgb color, an inline color or background, or plain Tailwind colors (text-gray-900, bg-white, text-black): they stay the same in dark mode, and inherited text is dark there.
- A preview of page content (a swatch, a tile showing a style) wears the colors the page will get: put `"data-preview": ""` on its outer element and style inside it freely.
- Lay out with flex, flex-col, grid, grid-cols-2/3, aspect-square, items-center, justify-between, gap-1/2/3, p-3, px-3, py-2, w-full, truncate, overflow-hidden, rounded-4, cursor-pointer, hover:bg-surface-gray-2, and type with text-base (panel title), text-sm, text-p-sm (sentences), text-xs, font-medium. Other Tailwind classes may not exist at runtime.
- A panel looks like: h("div", {class: "flex flex-col gap-3 p-3"}, [h(FormControl, {placeholder: "Search icons", modelValue: query.value, "onUpdate:modelValue": (value) => (query.value = value)}), h("div", {class: "grid grid-cols-3 gap-2"}, items.value.map(tile))])
- The editor test-renders your components in dark mode and sends back inline colors outside data-preview, unreadable text and hand-drawn controls for you to fix.

## Changing the page
When the plugin changes the page, the change must look the same once published:
- Add a block with insertBlock(options), and change one through the Block API (setStyle, setAttribute), so it saves with the page. CSS a block needs beyond its own styles (@keyframes, media queries) goes into a Builder Client Script of script_type "CSS" attached to the page, never a <style> in the editor.
- A block is {element, attributes, innerHTML, baseStyles, mobileStyles, children}. An image: {element: "img", attributes: {src, alt}, baseStyles: {width: "320px", objectFit: "cover"}}. An icon or shape: {element: "div", originalElement: "__raw_html__", innerHTML: "<svg ...>", baseStyles: {width: "48px", height: "48px"}}.
- The page publishes its root block as <body>, sized by its content, while the canvas draws it at the frame's height. A background meant to fill the screen needs minHeight "100vh" on the root block (block.isRoot()).
- Page CSS already on the page loads after block styles and wins a tie, so check pageStore.activePageScripts for rules on the same block or property before you rely on yours.

## "builder" exports
- Registries, each `register(item)` returning its unregister. Prefix item names with the plugin name and keep them stable across edits.
  leftPanelTabs: {name, label, icon, component}. A tab in the left bar.
  toolbarItems: {name, region: "left"|"center"|"right", component}
  blockContextMenuOptions: {name, label, action: ({block}) => void, condition?: ({block}) => boolean}
  settingsItems: {name, label, title, icon, group: "Current Page"|"Global", component}
  propertySections: {name, properties: [{component, getProps: () => ({}), searchKeyWords: "words"}]}
- insertBlock(options) adds a block inside the selected container, after any other selected block, or at the end of the page, selects it and returns it. For drag and drop, give the tile `draggable: true` and `onDragstart: (event) => startBlockDrag(event, options)`; the canvas shows its drop line and inserts the block where it lands. Offer both on every insert tile: click inserts, drag places.
- lucideIcon("lucide-<name>") for every icon field, e.g. `icon: lucideIcon("lucide-image-off")`. A plain string draws nothing.
- usePageStore(): pageBlocks[0] is the root Block, activePage the Builder Page doc. useBuilderStore(): leftPanelActiveTab = a tab name opens it. useCanvasStore().
- blockController.getSelectedBlocks(), blockController.getFirstSelectedBlock(); read them inside a computed so the panel follows the selection.
- A Block has blockId, element, children, getTextContent(), getStyle(prop), setStyle(prop, value), getAttribute(name), setAttribute(name, value), isText(), isImage(), isContainer(), selectBlock(), getParentBlock(). Walk `children` to visit the tree.
"frappe-ui": the components above, call(method, args) and createResource for whitelisted methods with the user's own permissions, toast.success/toast.error.
`context`: name, label, state.get()/state.set(values)/state.unset(key) (stored per user), setOpenHandler(fn): set it so the Open button shows the plugin, e.g. `() => (useBuilderStore().leftPanelActiveTab = "<tab name>")`.
