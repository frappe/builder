import { describe, expect, it } from "vitest";
import { extractNumberAndUnit } from "./cssUtils";

describe("extractNumberAndUnit", () => {
	it("splits a value into its number and unit", () => {
		expect(extractNumberAndUnit("10px")).toEqual({ number: "10", unit: "px" });
		expect(extractNumberAndUnit("1.5em")).toEqual({ number: "1.5", unit: "em" });
		expect(extractNumberAndUnit("20")).toEqual({ number: "20", unit: "" });
	});

	// arrow keys and drag step from this number, so a lost sign jumps -10px to 11px
	it("keeps the sign of a negative value", () => {
		expect(extractNumberAndUnit("-10px")).toEqual({ number: "-10", unit: "px" });
		expect(extractNumberAndUnit("-45deg")).toEqual({ number: "-45", unit: "deg" });
		expect(extractNumberAndUnit("-1")).toEqual({ number: "-1", unit: "" });
	});
});
