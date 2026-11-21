import { describe, expect, it, vi } from "vitest";

const canvasStore = vi.hoisted(() => ({
	activeCanvas: null as { getRootBlock: () => unknown } | null,
	selectBlock: () => {},
}));
vi.mock("@/stores/canvasStore", () => ({ default: () => canvasStore }));
vi.mock("@/stores/componentStore", () => ({ default: () => ({}) }));
vi.mock("@/translation", () => ({ __: (text: string) => text }));
vi.mock("frappe-ui", () => ({ toast: {}, dialog: vi.fn(), FileUploadHandler: class {} }));
vi.mock("@/utils/editorDemo", () => ({ editorDemo: {} }));

import Block from "@/block";
import { makeIdsUnique } from "./elementIds";

const link = (href: string) => ({ element: "a", attributes: { href } });

// an opener and the overlay it opens, with a link back to a page section
const makeOverlay = () =>
	new Block({
		element: "div",
		children: [
			link("#overlay"),
			{ element: "div", attributes: { id: "overlay" }, children: [link("#close"), link("#about")] },
		],
	} as BlockOptions);

const makePage = (...children: Block[]) => {
	const page = new Block({ element: "div", attributes: { id: "about" } } as BlockOptions);
	children.forEach((child) => {
		child.parentBlock = page;
		page.children.push(child);
	});
	return page;
};

const describeOverlay = (overlay: Block) => {
	const [opener, panel] = overlay.getChildren();
	return {
		opens: opener.getAttribute("href"),
		id: panel.getId(),
		links: panel.getChildren().map((child) => child.getAttribute("href")),
	};
};

describe("makeIdsUnique", () => {
	it("keeps ids the page does not use yet", () => {
		const overlay = makeOverlay();
		makeIdsUnique(overlay, makePage());

		expect(describeOverlay(overlay)).toEqual({
			opens: "#overlay",
			id: "overlay",
			links: ["#close", "#about"],
		});
	});

	it("renames ids the page already uses and points the block's own links at them", () => {
		const overlay = makeOverlay();
		makeIdsUnique(overlay, makePage(makeOverlay()));

		expect(describeOverlay(overlay)).toEqual({
			opens: "#overlay-2",
			id: "overlay-2",
			links: ["#close", "#about"],
		});
	});

	it("counts on from the last copy", () => {
		const second = makeOverlay();
		const page = makePage(makeOverlay());
		makeIdsUnique(second, page);
		page.children.push(second);

		const third = makeOverlay();
		makeIdsUnique(third, page);

		expect(describeOverlay(third).id).toBe("overlay-3");
	});
});

describe("Block.duplicateBlock", () => {
	it("gives the copy its own ids and points its links at them", () => {
		const overlay = makeOverlay();
		const page = makePage(overlay);
		canvasStore.activeCanvas = { getRootBlock: () => page };

		overlay.duplicateBlock();
		const [original, copy] = page.getChildren();

		expect(describeOverlay(original)).toEqual({
			opens: "#overlay",
			id: "overlay",
			links: ["#close", "#about"],
		});
		expect(describeOverlay(copy)).toEqual({
			opens: "#overlay-2",
			id: "overlay-2",
			links: ["#close", "#about"],
		});
	});
});
