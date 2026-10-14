import type Block from "@/block";
import { describe, expect, it, vi } from "vitest";
import { assertCanRepeat } from "../blockBindings";
import { readBlockFields, writeBlockFields } from "../blockFields";

// DOMPurify needs a browser. These tests check the table, not the markup rules
vi.mock("../safeMarkup", () => ({
	readElement: (value: unknown) => value,
	readHTML: (value: unknown) => value,
	readAttributes: (value: Record<string, unknown>) =>
		Object.fromEntries(Object.entries(value).map(([name, sent]) => [name, sent ?? undefined])),
}));

const fakeBlock = (overrides: Record<string, unknown> = {}) =>
	({
		dataKey: null,
		customAttributes: {},
		setStyle: vi.fn(),
		setAttribute: vi.fn(),
		setInnerHTML: vi.fn(),
		isRoot: () => false,
		isRepeater: () => false,
		canHaveChildren: () => true,
		getElement: () => "div",
		...overrides,
	}) as unknown as Block;

const refusal = (run: () => unknown) => {
	try {
		run();
	} catch (error) {
		return (error as { code?: string }).code;
	}
	return "no refusal";
};

describe("readBlockFields", () => {
	it("reads every field that block.get returns", () => {
		const sent = {
			element: "section",
			classes: ["card"],
			blockName: "Card",
			baseStyles: { color: "red" },
			customAttributes: { "data-id": "1" },
			dynamicValues: [{ key: "title", type: "key", property: "innerHTML" }],
			props: { label: { value: "Hi" } },
		};

		expect(Object.keys(readBlockFields(sent, "div", []))).toEqual([
			"element",
			"customAttributes",
			"classes",
			"baseStyles",
			"blockName",
			"dynamicValues",
			"props",
		]);
	});

	it("keeps the method's own params out of the fields", () => {
		expect(readBlockFields({ blockId: "a", breakpoint: "mobile", classes: [] }, "div", ["blockId", "breakpoint"])).toEqual({
			classes: [],
		});
	});

	it.each([
		["an unknown field", { colour: "red" }],
		["a block client script, which the editor cannot show", { clientScript: { js: "x" } }],
		["Builder's own bookkeeping", { blockId: "a" }],
		["a dynamic value with no property", { dynamicValues: [{ key: "title", type: "key" }] }],
		["a style that is not text", { styles: { color: { r: 1 } } }],
		["a prop with an unknown setting", { props: { label: { colour: "red" } } }],
	])("refuses %s", (_case, sent) => {
		expect(refusal(() => readBlockFields(sent, "div", []))).toBe("invalid_params");
	});

	it("names the nested field in a refusal", () => {
		expect(() => readBlockFields({ dataKey: { key: "" } }, "div", [], "block.")).toThrow('"block.dataKey.key"');
	});

	it("fills a prop with Builder's defaults", () => {
		expect(readBlockFields({ props: { label: { value: "Hi" } } }, "div", []).props).toEqual({
			label: { isDynamic: false, isPassedDown: false, comesFrom: null, value: "Hi" },
		});
	});
});

describe("writeBlockFields", () => {
	it("writes a cleared data key as an empty object, which the server can read", () => {
		const block = fakeBlock({ dataKey: { key: "posts" } });

		writeBlockFields(block, readBlockFields({ isRepeaterBlock: false, dataKey: null }, "div", []));

		expect(block.dataKey).toEqual({});
		expect(block.isRepeaterBlock).toBe(false);
	});

	it("writes each style map to its own breakpoint", () => {
		const block = fakeBlock();

		writeBlockFields(block, readBlockFields({ mobileStyles: { color: "red" }, styles: { gap: "4px" } }, "div", []), "tablet");

		expect(block.setStyle).toHaveBeenCalledWith("color", "red", "mobile");
		expect(block.setStyle).toHaveBeenCalledWith("gap", "4px", "tablet");
	});

	it("merges custom attributes, and null removes one", () => {
		const block = fakeBlock({ customAttributes: { a: "1", b: "2" } });

		writeBlockFields(block, readBlockFields({ customAttributes: { a: null, c: "3" } }, "div", []));

		expect(block.customAttributes).toEqual({ b: "2", c: "3" });
	});
});

describe("assertCanRepeat", () => {
	const repeat = { isRepeaterBlock: true, dataKey: { key: "posts" } };

	it("accepts a container with a list key", () => {
		expect(refusal(() => assertCanRepeat(repeat, fakeBlock()))).toBe("no refusal");
	});

	it.each([
		["the page root", fakeBlock({ isRoot: () => true })],
		["a block that cannot have children", fakeBlock({ canHaveChildren: () => false })],
	])("refuses a repeater on %s", (_case, block) => {
		expect(refusal(() => assertCanRepeat(repeat, block))).toBe("invalid_params");
	});

	it("refuses a repeater with no list key", () => {
		expect(refusal(() => assertCanRepeat({ isRepeaterBlock: true }, fakeBlock()))).toBe("invalid_params");
	});

	it("ignores a patch that does not touch the loop", () => {
		expect(refusal(() => assertCanRepeat({ blockName: "Posts" }, fakeBlock({ isRepeater: () => true })))).toBe(
			"no refusal",
		);
	});
});
