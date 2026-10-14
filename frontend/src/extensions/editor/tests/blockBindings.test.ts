import type Block from "@/block";
import { describe, expect, it } from "vitest";
import { assertCanRepeat, readBindings, writeBindings } from "../blockBindings";

const fakeBlock = (overrides: Record<string, unknown> = {}) =>
	({
		dataKey: null,
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

describe("readBindings", () => {
	it("keeps only the fields that the patch names", () => {
		expect(readBindings({ attributes: {}, blockName: "Title" })).toEqual({ blockName: "Title" });
	});

	it("keeps null, which clears a field", () => {
		expect(readBindings({ dataKey: null, visibilityCondition: null })).toEqual({
			dataKey: null,
			visibilityCondition: null,
		});
	});

	it("gives a dynamic value the data script as its source by default", () => {
		const { dynamicValues } = readBindings({
			dynamicValues: [{ key: "title", type: "key", property: "innerHTML" }],
		});

		expect(dynamicValues).toEqual([{ key: "title", type: "key", property: "innerHTML", comesFrom: "dataScript" }]);
	});

	it.each([
		["a dynamic value with no property", { dynamicValues: [{ key: "title", type: "key" }] }],
		["an unknown binding type", { dynamicValues: [{ key: "a", type: "class", property: "x" }] }],
		["an unknown source", { dataKey: { key: "posts", comesFrom: "url" } }],
		["a data key with no key", { dataKey: { property: "innerHTML" } }],
		["a repeater flag that is not a boolean", { isRepeaterBlock: "yes" }],
		["too many dynamic values", { dynamicValues: Array(51).fill({ key: "a", type: "key", property: "x" }) }],
	])("refuses %s", (_case, patch) => {
		expect(refusal(() => readBindings(patch))).toBe("invalid_params");
	});

	it("names the nested field in a refusal", () => {
		expect(() => readBindings({ dataKey: { key: "" } }, "block.")).toThrow('"block.dataKey.key"');
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

	it("refuses a cleared key on a block that stays a repeater", () => {
		const block = fakeBlock({ isRepeater: () => true, dataKey: { key: "posts" } });

		expect(refusal(() => assertCanRepeat({ dataKey: null }, block))).toBe("invalid_params");
	});

	it("ignores a patch that does not touch the loop", () => {
		const oldRepeater = fakeBlock({ isRepeater: () => true });

		expect(refusal(() => assertCanRepeat({ blockName: "Posts" }, oldRepeater))).toBe("no refusal");
	});
});

describe("writeBindings", () => {
	it("writes a cleared data key as an empty object, which the server can read", () => {
		const block = fakeBlock({ dataKey: { key: "posts" } });

		writeBindings(block, { isRepeaterBlock: false, dataKey: null });

		expect(block.dataKey).toEqual({});
		expect(block.isRepeaterBlock).toBe(false);
	});
});
