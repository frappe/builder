import { beforeEach, describe, expect, it, vi } from "vitest";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

class FakeBlock {
	static count = 0;
	blockId = `block-${++FakeBlock.count}`;
	attributes: Record<string, string | undefined> = {};
	styles: Record<string, unknown> = {};
	classes: string[] = [];
	innerHTML?: string;
	children: FakeBlock[] = [];

	constructor(public element = "div") {}

	setAttribute(attribute: string, value: string | undefined) {
		this.attributes[attribute] = value;
	}
	setStyle(style: string, value: unknown) {
		this.styles[style] = value;
	}
	setInnerHTML(innerHTML: string) {
		this.innerHTML = innerHTML;
	}
	addChild(options: { element: string; classes?: string[]; innerHTML?: string }) {
		const child = Object.assign(new FakeBlock(options.element), {
			classes: options.classes ?? [],
			innerHTML: options.innerHTML,
		});
		this.children.push(child);
		return child;
	}
}

let root: FakeBlock;
const findBlock = (blockId: string) => (blockId === root.blockId ? root : undefined);

vi.mock("@/stores/canvasStore", () => ({
	default: () => ({ activeCanvas: { findBlock, selectedBlockIds: [], clearSelection: () => {} } }),
}));
vi.mock("@/utils/helpers", () => ({ getBlockObject: (block: unknown) => block }));

const { blockMethods } = await import("../blockMethods");

const extension = { name: "tools" } as InstalledExtension;
const call = (method: string, params: unknown) => blockMethods[method].run(params, extension);

beforeEach(() => {
	root = new FakeBlock();
});

describe("block.update", () => {
	it("clears the text and sets an empty attribute", () => {
		root.innerHTML = "Old";
		call("block.update", { blockId: root.blockId, innerHTML: "", attributes: { alt: "" } });

		expect(root.innerHTML).toBe("");
		expect(root.attributes.alt).toBe("");
	});
});

describe("block.insert", () => {
	it("accepts empty text", () => {
		call("block.insert", { parentId: root.blockId, block: { element: "p", innerHTML: "" } });

		expect(root.children[0].innerHTML).toBe("");
	});
});
