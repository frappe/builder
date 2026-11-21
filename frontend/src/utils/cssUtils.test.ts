import { describe, expect, it } from "vitest";
import { toUnitOf } from "./cssUtils";

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
