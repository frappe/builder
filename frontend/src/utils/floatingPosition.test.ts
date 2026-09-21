import { describe, expect, it } from "vitest";
import { placeWithinBounds } from "./floatingPosition";

const bounds = { left: 0, top: 0, right: 1000, bottom: 600, width: 1000, height: 600 };
const size = { width: 200, height: 40 };

describe("placeWithinBounds", () => {
	it("centers at the top when there is no position yet", () => {
		expect(placeWithinBounds(bounds, size, null)).toEqual({ x: 400, y: 12 });
	});

	it("keeps a position that is already inside", () => {
		expect(placeWithinBounds(bounds, size, { x: 120, y: 400 })).toEqual({ x: 120, y: 400 });
	});

	it("pulls a position outside the bounds back in", () => {
		expect(placeWithinBounds(bounds, size, { x: 2000, y: -50 })).toEqual({ x: 788, y: 12 });
	});

	it("offsets by the bounds, not the viewport", () => {
		const offsetBounds = { ...bounds, left: 300, right: 1300 };
		expect(placeWithinBounds(offsetBounds, size, { x: 0, y: 100 })).toEqual({ x: 312, y: 100 });
	});
});
