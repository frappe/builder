import { describe, expect, it } from "vitest";
import { getNumberInUnit } from "./cssUtils";

describe("getNumberInUnit", () => {
	it("reads values in the given unit", () => {
		expect(getNumberInUnit("10px", "px")).toBe(10);
		expect(getNumberInUnit(" -20px ", "px")).toBe(-20);
		expect(getNumberInUnit("10PX", "px")).toBe(10);
		expect(getNumberInUnit("1.5em", "em")).toBe(1.5);
	});

	it("treats a unitless number as the given unit", () => {
		expect(getNumberInUnit("20", "px")).toBe(20);
		expect(getNumberInUnit(20, "px")).toBe(20);
		expect(getNumberInUnit(0, "px")).toBe(0);
	});

	it("rejects another unit", () => {
		expect(getNumberInUnit("50%", "px")).toBeNull();
		expect(getNumberInUnit("50vw", "px")).toBeNull();
	});

	it("rejects values it cannot read as a number", () => {
		expect(getNumberInUnit("", "px")).toBeNull();
		expect(getNumberInUnit("auto", "px")).toBeNull();
		expect(getNumberInUnit("calc(50% - 10px)", "px")).toBeNull();
		expect(getNumberInUnit("10px 20px", "px")).toBeNull();
		expect(getNumberInUnit(null, "px")).toBeNull();
		expect(getNumberInUnit(undefined, "px")).toBeNull();
		expect(getNumberInUnit(false, "px")).toBeNull();
	});
});
