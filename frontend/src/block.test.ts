import { describe, expect, it, vi } from "vitest";

vi.mock("@/stores/canvasStore", () => ({ default: () => ({ activeCanvas: null, selectBlock: vi.fn() }) }));
vi.mock("@/stores/componentStore", () => ({ default: () => ({}) }));
vi.mock("@/translation", () => ({ __: (text: string) => text }));
vi.mock("frappe-ui", () => ({ toast: {}, dialog: vi.fn(), FileUploadHandler: class {} }));
vi.mock("@/utils/editorDemo", () => ({ editorDemo: {} }));

import Block from "@/block";

describe("Block.setStyle", () => {
	it("keeps a hyphenated state name and camel-cases only the property", () => {
		const block = new Block({ blockId: "panel" } as BlockOptions);
		block.setStyle("focus-visible:outline-color" as styleProperty, "blue");
		block.setStyle("focus-within:border-color" as styleProperty, "red");
		block.setStyle("target:visibility" as styleProperty, "visible");

		expect(block.baseStyles).toEqual({
			"focus-visible:outlineColor": "blue",
			"focus-within:borderColor": "red",
			"target:visibility": "visible",
		});
		expect(block.getStyle("focus-visible:outlineColor" as styleProperty)).toBe("blue");
	});
});

describe("Block.isVisible", () => {
	it("reads a state's display while that state applies", () => {
		const block = new Block({
			blockId: "panel",
			baseStyles: { display: "none", "target:display": "flex" },
			mobileStyles: { "target:display": "none" },
		} as unknown as BlockOptions);

		expect(block.isVisible("desktop")).toBe(false);
		expect(block.isVisible("desktop", "target")).toBe(true);
		expect(block.isVisible("desktop", "hover")).toBe(false);
		expect(block.isVisible("mobile", "target")).toBe(false);
	});

	it("counts a block hidden until linked to as visible on the selection path", () => {
		const block = new Block({
			blockId: "panel",
			baseStyles: { display: "none", "target:display": "flex" },
			mobileStyles: { "target:display": "none" },
		} as unknown as BlockOptions);
		const hidden = new Block({
			blockId: "hidden",
			baseStyles: { display: "none" },
		} as unknown as BlockOptions);

		expect(block.isVisibleOnSelectionPath("desktop")).toBe(true);
		expect(block.isVisibleOnSelectionPath("mobile")).toBe(false);
		expect(hidden.isVisibleOnSelectionPath("desktop")).toBe(false);
	});
});

describe("Block.duplicateBlock", () => {
	it("shifts a copy placed in % by a % and one placed in px by px", () => {
		const pin = (blockId: string, left: string, top: string) => ({
			blockId,
			baseStyles: { position: "absolute", left, top },
		});
		const map = new Block({
			blockId: "map",
			baseStyles: { position: "relative" },
			children: [pin("percent", "38.4%", "30%"), pin("pixels", "120px", "40px")],
		} as unknown as BlockOptions);
		const [percent, pixels] = map.children;

		percent.duplicateBlock();
		pixels.duplicateBlock();

		const positions = map.children.map((block) => [block.getStyle("left"), block.getStyle("top")]);
		expect(positions).toEqual([
			["38.4%", "30%"],
			["40.4%", "32%"],
			["120px", "40px"],
			["140px", "60px"],
		]);
	});
});
