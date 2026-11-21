import type Block from "@/block";
import { describe, expect, it, vi } from "vitest";
import { computed, nextTick, ref } from "vue";
import { useBlockSelection } from "./useBlockSelection";

vi.mock("@/utils/helpers", () => ({ generateId: () => "id" }));

type FakeBlock = {
	blockId: string;
	children: FakeBlock[];
	parentBlock: FakeBlock | null;
	getParentBlock: () => FakeBlock | null;
};

const makeBlock = (blockId: string, children: FakeBlock[] = []): FakeBlock => {
	const block: FakeBlock = { blockId, children, parentBlock: null, getParentBlock: () => block.parentBlock };
	children.forEach((child) => (child.parentBlock = block));
	return block;
};

// body > section > panel > text, and body > footer
const makePage = () => {
	const text = makeBlock("text");
	const panel = makeBlock("panel", [text]);
	const section = makeBlock("section", [panel]);
	const footer = makeBlock("footer");
	const body = makeBlock("body", [section, footer]);
	const blocks = { body, section, panel, text, footer };
	const selection = useBlockSelection(ref(body as unknown as Block));
	return { blocks: blocks as unknown as Record<keyof typeof blocks, Block>, selection };
};

const pathOf = (selection: ReturnType<typeof useBlockSelection>, blocks: Record<string, Block>) =>
	Object.keys(blocks).filter((name) => selection.isOnSelectionPath(blocks[name]));

describe("useBlockSelection", () => {
	it("puts a selected block and its ancestors on the selection path", async () => {
		const { blocks, selection } = makePage();
		selection.selectBlock(blocks.panel);
		await nextTick();

		expect(pathOf(selection, blocks)).toEqual(["body", "section", "panel"]);
	});

	it("follows every block of a multiple selection", async () => {
		const { blocks, selection } = makePage();
		selection.selectBlock(blocks.text);
		selection.selectBlock(blocks.footer, true);
		await nextTick();
		expect(pathOf(selection, blocks)).toEqual(["body", "section", "panel", "text", "footer"]);

		selection.toggleBlockSelection(blocks.text);
		await nextTick();
		expect(pathOf(selection, blocks)).toEqual(["body", "footer"]);
	});

	it("empties the selection path when the selection is cleared", async () => {
		const { blocks, selection } = makePage();
		selection.selectBlock(blocks.text);
		await nextTick();
		selection.clearSelection();
		await nextTick();

		expect(pathOf(selection, blocks)).toEqual([]);
	});

	it("reruns a block's check only when that block joins or leaves the path", async () => {
		const { blocks, selection } = makePage();
		const runs: Record<string, number> = {};
		const checks = Object.entries(blocks).map(([name, block]) =>
			computed(() => {
				runs[name] = (runs[name] || 0) + 1;
				return selection.isOnSelectionPath(block);
			}),
		);
		const readAll = () => checks.forEach((check) => check.value);

		selection.selectBlock(blocks.text);
		await nextTick();
		readAll();
		const runsAfterFirstRead = { ...runs };

		selection.selectBlock(blocks.footer);
		await nextTick();
		readAll();

		const reran = Object.keys(runs).filter((name) => runs[name] > runsAfterFirstRead[name]);
		expect(reran).toEqual(["section", "panel", "text", "footer"]);
	});
});
