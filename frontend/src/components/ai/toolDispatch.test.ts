import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

vi.mock("@/utils/helpers", () => ({
	getBlockInstance: (block: Record<string, any>) => ({ ...block }),
	kebabToCamelCase: (name: string) => name.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase()),
}));
vi.mock("@/utils/block/tree", () => ({
	findBlockInTree: (id: string, blocks: any[]) => blocks.find((block) => block.blockId === id),
}));
vi.mock("./lucideIcon", () => ({ lucideSVG: () => '<svg viewBox="0 0 24 24"><path d="M0 0"/></svg>' }));

import { ToolDispatcher } from "./toolDispatch";
import { normalizeStyles } from "./normalizeStyles";
import { convertYAMLtoBlock } from "./yaml";

let dispatcher: ToolDispatcher;
let block: any;
let store: any;
let canvas: any;
beforeEach(() => {
	block = {
		blockId: "hero",
		element: "div",
		baseStyles: {},
		mobileStyles: {},
		tabletStyles: {},
		attributes: {},
		customAttributes: {},
		dynamicValues: [],
		classes: [],
		setAttribute(key: string, value: unknown) {
			this.attributes[key] = value;
		},
		setInnerHTML(value: string) {
			this.innerHTML = value;
		},
	};
	store = {
		activePage: { name: "page", page_data_script: "" },
		pageBlocks: [],
		applyRepeaterDataScript: vi.fn(),
		setPageData: vi.fn(),
		activePageScripts: [],
	};
	canvas = { getRootBlock: () => block, setRootBlock: vi.fn() };
	dispatcher = new ToolDispatcher(store, ref(canvas));
});

describe("canonical accepted block operations", () => {
	it("preserves normalized nulls and deletes styles at all breakpoints", () => {
		expect(normalizeStyles({ "margin-top": null, "hover:background-color": null, "--brand": null })).toEqual({
			marginTop: null,
			"hover:backgroundColor": null,
			"--brand": null,
		});
		block.baseStyles = { marginTop: "10px", color: "red", "--brand": "pink" };
		block.mobileStyles = { paddingTop: "4px", display: "flex" };
		block.tabletStyles = { "hover:backgroundColor": "pink", width: "80px" };
		dispatcher.applyToolOperation("update_block", {
			block_id: "hero",
			base_styles: { "margin-top": null, "--brand": null },
			mobile_styles: { "padding-top": null, gap: 8 },
			tablet_styles: { "hover:background-color": null },
		});
		expect(block.baseStyles).toEqual({ color: "red" });
		expect(block.mobileStyles).toEqual({ display: "flex", gap: "8px" });
		expect(block.tabletStyles).toEqual({ width: "80px" });
	});

	it("keeps font stacks and state-scoped custom properties intact", () => {
		expect(
			normalizeStyles({
				fontFamily: "var(--DisplayFont, 'Open Sans'), serif",
				"hover:--BrandFont": "'Newsreader', serif",
			}),
		).toEqual({
			fontFamily: "var(--DisplayFont, 'Open Sans'), serif",
			"hover:--BrandFont": "'Newsreader', serif",
		});
	});

	it("clears both attribute stores before setting or unsetting each canonical key", () => {
		block.attributes = { id: "legacy", href: "/old", "aria-label": "stale" };
		block.customAttributes = { id: "current", href: "/also-old", "aria-label": "current" };
		dispatcher.applyToolOperation("update_block", {
			block_id: "hero",
			attributes: { id: "new", href: "/new", "aria-label": null },
		});
		expect(block.attributes).toEqual({ href: "/new" });
		expect(block.customAttributes).toEqual({ id: "new" });
		dispatcher.applyToolOperation("update_block", { block_id: "hero", attributes: { id: null, href: null } });
		expect(block.attributes).toEqual({});
		expect(block.customAttributes).toEqual({});
	});

	it("applies ordered accepted patches with text/html precedence and null unbinding", () => {
		dispatcher.applyToolOperation("update_block", {
			block_id: "hero",
			base_styles: { width: "12px" },
			inner_text: "plain",
			inner_html: "<b>final</b>",
			bind: { text: "item.title" },
		});
		dispatcher.applyToolOperation("update_block", {
			block_id: "hero",
			base_styles: { width: null },
			bind: { text: null },
		});
		expect(block.baseStyles).toEqual({});
		expect(block.innerHTML).toBe("<b>final</b>");
		expect(block.dynamicValues).toEqual([]);
	});
});

describe("server-authoritative generation", () => {
	it("mirrors expanded blocks and compiled data without persisting them again", () => {
		const canonical = { blockId: "server-root", element: "body", children: [] };
		const script = "data['items'] = [{'enabled': True, 'extra': None}]";
		dispatcher.applyToolOperation("generate_page", {
			blocks: [canonical],
			data_script: script,
			yaml: "el: wrong",
		});
		expect(canvas.setRootBlock).toHaveBeenCalledWith(canonical, false, true);
		expect(store.activePage.page_data_script).toBe(script);
		expect(store.setPageData).toHaveBeenCalledWith(store.activePage);
		expect(store.applyRepeaterDataScript).not.toHaveBeenCalled();
	});

	it("does not treat a legacy YAML-only final payload as authoritative", () => {
		dispatcher.applyToolOperation("generate_page", {
			yaml: "el: body\nrepeat:\n  data: items\n  items: [{enabled: true}]\n  item: {el: div}",
		});
		expect(canvas.setRootBlock).not.toHaveBeenCalled();
		expect(store.applyRepeaterDataScript).not.toHaveBeenCalled();
		expect(store.setPageData).not.toHaveBeenCalled();
	});

	it("keeps streamed YAML preview-only even when it contains inline data", () => {
		dispatcher.applyPageYaml(
			"el: body\nc:\n  - el: div\n    repeat:\n      data: items\n      items: [{enabled: true, extra: null}]\n      item: {el: span, text: Item}",
		);
		expect(canvas.setRootBlock).toHaveBeenCalledWith(
			expect.objectContaining({ element: "body" }),
			false,
			false,
		);
		expect(store.applyRepeaterDataScript).not.toHaveBeenCalled();
		expect(store.setPageData).not.toHaveBeenCalled();
	});

	it("retains explicit icon unsets, references, attributes and responsive styles in previews", () => {
		const icon = convertYAMLtoBlock({
			icon: "star",
			ref: "icon-ref",
			style: { display: null, width: null, "flex-shrink": null, color: "blue" },
			m_style: { "margin-top": 4 },
			t_style: { width: null, height: 30 },
			attrs: { id: "mark", title: "Star", "aria-label": "Logo" },
			classes: ["brand"],
		});
		expect(icon.blockId).toBe("icon-ref");
		expect(icon.baseStyles).not.toHaveProperty("display");
		expect(icon.baseStyles).not.toHaveProperty("width");
		expect(icon.baseStyles).not.toHaveProperty("flexShrink");
		expect(icon.baseStyles?.color).toBe("blue");
		expect(icon.mobileStyles).toEqual({ marginTop: "4px" });
		expect(icon.tabletStyles).toEqual({ height: "30px" });
		expect(icon.attributes).toEqual({ title: "Star" });
		expect(icon.customAttributes).toEqual({ "data-lucide": "star", id: "mark", "aria-label": "Logo" });
		expect(icon.classes).toEqual(["brand"]);
	});
});
