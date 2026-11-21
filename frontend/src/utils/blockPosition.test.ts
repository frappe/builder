import { beforeEach, describe, expect, it, vi } from "vitest";

const canvasStore = vi.hoisted(() => ({
	activeCanvas: { activeBreakpoint: "desktop" },
	selectBlock: () => {},
}));
vi.mock("@/stores/canvasStore", () => ({ default: () => canvasStore }));
vi.mock("@/stores/componentStore", () => ({ default: () => ({}) }));
vi.mock("@/translation", () => ({ __: (text: string) => text }));
vi.mock("frappe-ui", () => ({ toast: {}, dialog: vi.fn(), FileUploadHandler: class {} }));
vi.mock("@/utils/editorDemo", () => ({ editorDemo: {} }));

import Block from "@/block";
import BlockPosition from "@/utils/blockPosition";

const blockWith = (baseStyles: Record<string, string>) =>
	new Block({ blockId: "badge", baseStyles } as unknown as BlockOptions);

describe("BlockPosition.apply", () => {
	beforeEach(() => {
		canvasStore.activeCanvas.activeBreakpoint = "desktop";
	});

	it("overrides a side a wider breakpoint pins with auto, since clearing would bring it back", () => {
		const block = blockWith({ position: "absolute", left: "20px", width: "100px", translate: "-50% 0" });
		canvasStore.activeCanvas.activeBreakpoint = "mobile";

		new BlockPosition(block, null).apply({ left: null, right: "12px", width: null, translate: null });

		expect(block.mobileStyles).toEqual({ left: "auto", right: "12px", width: "auto", translate: "none" });
		expect(block.baseStyles).toEqual({
			position: "absolute",
			left: "20px",
			width: "100px",
			translate: "-50% 0",
		});
	});

	it("drops a side set on the breakpoint being edited", () => {
		const block = blockWith({ position: "absolute", left: "20px", right: "12px" });

		new BlockPosition(block, null).apply({ left: null });

		expect(block.baseStyles).toEqual({ position: "absolute", right: "12px" });
	});

	it("splits an inset shorthand into the sides before editing one", () => {
		const block = blockWith({ position: "absolute", inset: "0" });

		new BlockPosition(block, null).apply({ bottom: null, height: "80px" });

		expect(block.baseStyles).toEqual({
			position: "absolute",
			top: "0",
			right: "0",
			left: "0",
			height: "80px",
		});
	});
});

describe("BlockPosition.setType", () => {
	it("turns a free block sticky to the top, dropping the offsets that placed it", () => {
		const block = blockWith({ position: "absolute", right: "16px", bottom: "16px" });

		new BlockPosition(block, null).setType("sticky");

		expect(block.baseStyles).toEqual({ position: "sticky", top: "0px" });
	});

	it("clears the pins and the centring when a block goes back into the flow", () => {
		const block = blockWith({ position: "absolute", left: "50%", top: "8px", translate: "-50% 0" });

		new BlockPosition(block, null).setType("relative");

		expect(block.baseStyles).toEqual({ position: "relative" });
	});
});
