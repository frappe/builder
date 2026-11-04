import { beforeEach, describe, expect, it, vi } from "vitest";

const selection = vi.hoisted(() => ({ block: null as unknown }));
const root = vi.hoisted(() => ({ addChild: vi.fn() }));

vi.mock("@/utils/blockController", () => ({
	default: { getFirstSelectedBlock: () => selection.block },
}));
vi.mock("@/stores/canvasStore", () => ({
	default: () => ({ activeCanvas: { getRootBlock: () => root }, handleDragStart: vi.fn() }),
}));
vi.mock("@/utils/helpers", () => ({
	getBlockInstance: (json: string, retainId: boolean) => ({ ...JSON.parse(json), retainId }),
}));

import { insertBlock } from "./blocks";

type FakeBlock = {
	canHaveChildren: () => boolean;
	addChild: ReturnType<typeof vi.fn>;
	addChildAfter: ReturnType<typeof vi.fn>;
	getParentBlock: () => FakeBlock | null;
	isChildOfComponent?: string;
};

const fakeBlock = (canHaveChildren: boolean, parent: FakeBlock | null = null, isChildOfComponent?: string) =>
	({
		canHaveChildren: () => canHaveChildren,
		addChild: vi.fn(),
		addChildAfter: vi.fn(),
		getParentBlock: () => parent,
		isChildOfComponent,
	}) as FakeBlock;

const icon = { element: "div", innerHTML: "<svg></svg>" };

describe("insertBlock", () => {
	beforeEach(() => {
		selection.block = null;
		root.addChild.mockClear();
	});

	it("adds to the end of the page when nothing is selected", () => {
		insertBlock(icon);

		expect(root.addChild).toHaveBeenCalledWith({ ...icon, retainId: false });
	});

	it("adds inside a selected container", () => {
		const section = fakeBlock(true);
		selection.block = section;

		insertBlock(icon);

		expect(section.addChild).toHaveBeenCalledWith({ ...icon, retainId: false }, undefined);
	});

	it("adds right after a selected block that takes no children", () => {
		const section = fakeBlock(true);
		const heading = fakeBlock(false, section);
		selection.block = heading;

		insertBlock(icon);

		expect(section.addChildAfter).toHaveBeenCalledWith({ ...icon, retainId: false }, heading);
	});

	it("adds beside a component instance when a block inside it is selected", () => {
		const section = fakeBlock(true);
		const instance = fakeBlock(false, section);
		selection.block = fakeBlock(true, instance, "header");

		insertBlock(icon);

		expect(section.addChildAfter).toHaveBeenCalledWith({ ...icon, retainId: false }, instance);
	});
});
