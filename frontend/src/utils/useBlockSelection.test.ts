import type Block from "@/block";
import { describe, expect, it, vi } from "vitest";
import { computed, reactive } from "vue";
import { getSelectionPathIds, syncSet } from "./useBlockSelection";

vi.mock("@/utils/helpers", () => ({ generateId: () => "id" }));

type FakeBlock = { blockId: string; parentBlock: FakeBlock | null; getParentBlock: () => FakeBlock | null };

const makeBlock = (blockId: string, parentBlock: FakeBlock | null = null): FakeBlock => {
	const block: FakeBlock = { blockId, parentBlock, getParentBlock: () => block.parentBlock };
	return block;
};

// body > section > panel > text, and body > footer
const makePage = () => {
	const body = makeBlock("body");
	const section = makeBlock("section", body);
	const panel = makeBlock("panel", section);
	const text = makeBlock("text", panel);
	const footer = makeBlock("footer", body);
	return { body, section, panel, text, footer } as unknown as Record<string, Block>;
};

describe("getSelectionPathIds", () => {
	it("holds each selected block and its ancestors", () => {
		const page = makePage();
		expect([...getSelectionPathIds([page.panel])]).toEqual(["panel", "section", "body"]);
		expect([...getSelectionPathIds([page.text, page.footer])]).toEqual([
			"text",
			"panel",
			"section",
			"body",
			"footer",
		]);
		expect(getSelectionPathIds([]).size).toBe(0);
	});
});

describe("syncSet", () => {
	it("updates the set in place, so a check on an unchanged entry does not rerun", () => {
		const path = reactive(new Set(["body", "section", "panel"]));
		const runs: Record<string, number> = {};
		const checks = ["body", "section", "panel", "footer"].map((id) =>
			computed(() => {
				runs[id] = (runs[id] || 0) + 1;
				return path.has(id);
			}),
		);
		const readAll = () => checks.map((check) => check.value);
		readAll();

		syncSet(path, new Set(["body", "footer"]));

		expect(readAll()).toEqual([true, false, false, true]);
		expect(runs).toEqual({ body: 1, section: 2, panel: 2, footer: 2 });
	});
});
