import { describe, expect, it } from "vitest";
import { addUnitToNumber, toUnitOf } from "./cssUtils";

describe("toUnitOf", () => {
	it("writes px as a share of the container when the value is a %", () => {
		expect(toUnitOf("40%", 300, 1000)).toBe("30%");
		expect(toUnitOf("40%", 123.456, 1000)).toBe("12.3%");
	});

	it("writes px for any other unit, or when the container has no size", () => {
		expect(toUnitOf("40px", 300.4, 1000)).toBe("300px");
		expect(toUnitOf(undefined, 300, 1000)).toBe("300px");
		expect(toUnitOf("40%", 300, 0)).toBe("300px");
	});
});

describe("addUnitToNumber", () => {
	it("adds the unit to a bare number only, so a typed keyword stays as typed", () => {
		expect(addUnitToNumber("35", "%")).toBe("35%");
		expect(addUnitToNumber("-4.5", "px")).toBe("-4.5px");
		expect(addUnitToNumber("12em", "px")).toBe("12em");
		expect(addUnitToNumber("auto", "px")).toBe("auto");
		expect(addUnitToNumber("calc(50% - 8px)", "px")).toBe("calc(50% - 8px)");
	});
});
