import { describe, expect, it, vi } from "vitest";

vi.mock("@/stores/canvasStore", () => ({ default: () => ({ activeCanvas: null }) }));
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
