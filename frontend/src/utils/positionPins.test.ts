import { describe, expect, it } from "vitest";
import { BlockPins, type AxisBox, type Box } from "./positionPins";

const pinsOf = (styles: Record<string, string>) => new BlockPins((property) => styles[property]);

// a 100 x 50 block in a 400 x 300 parent, 40px from the left and 20px from the top
const axisBox = (start: number, size: number, container: number): AxisBox => ({
	start,
	end: container - start - size,
	size,
	marginStart: 0,
	marginEnd: 0,
	container,
});
const box: Box = { x: axisBox(40, 100, 400), y: axisBox(20, 50, 300) };
// the same block centred: its layout box sits half its size right of and below where it shows
const centeredBox: Box = { x: axisBox(90, 100, 400), y: axisBox(45, 50, 300) };

describe("BlockPins reading", () => {
	it("reads a block with only top and left as pinned top-left", () => {
		const pins = pinsOf({ top: "20px", left: "40px" });
		expect([pins.x.pin, pins.y.pin, pins.custom]).toEqual(["start", "start", false]);
	});

	it("reads right, bottom, both sides and no sides", () => {
		expect(pinsOf({ right: "0px", bottom: "10%" }).x.pin).toBe("end");
		expect(pinsOf({ right: "0px", bottom: "10%" }).y.pin).toBe("end");
		expect(pinsOf({ left: "0px", right: "0px" }).x.pin).toBe("stretch");
		expect(pinsOf({ left: "auto", right: "8px" }).x.pin).toBe("end");
		expect(pinsOf({}).x.pin).toBe("none");
	});

	it("reads an inset shorthand as its four sides", () => {
		const pins = pinsOf({ inset: "0" });
		expect([pins.x.pin, pins.y.pin]).toEqual(["stretch", "stretch"]);
		expect(pinsOf({ inset: "10px auto auto 10px" }).x.pin).toBe("start");
	});

	it("reads left 50% with the centring translate as centred", () => {
		const pins = pinsOf({ left: "calc(50% - 12px)", top: "50%", translate: "-50% -50%" });
		expect([pins.x.pin, pins.y.pin, pins.custom]).toEqual(["center", "center", false]);
		expect(pinsOf({ left: "50%", top: "8px", translate: "-50%" }).y.pin).toBe("start");
	});

	it("reads a translate or transform it did not write as custom, pinned by its sides", () => {
		const transformed = pinsOf({ left: "22.9%", top: "30.6%", transform: "translate(-50%, -50%)" });
		expect([transformed.x.pin, transformed.y.pin, transformed.custom]).toEqual(["start", "start", true]);
		expect(pinsOf({ left: "20px", translate: "12px 12px" }).custom).toBe(true);
		expect(pinsOf({ left: "20px", translate: "-50% 0" }).custom).toBe(true);
		expect(pinsOf({ left: "20px", transform: "rotate(4deg)" }).custom).toBe(false);
	});
});

describe("BlockPins.toggle keeps the block where it is", () => {
	it("stretches a left-pinned block when its right side is pinned", () => {
		const patch = pinsOf({ left: "40px", top: "20px", width: "100px" }).toggle("x", "end", box);
		expect(patch).toEqual({ right: "260px", width: null });
	});

	it("gives a stretched block its rendered width back when a side is unpinned", () => {
		const patch = pinsOf({ left: "40px", right: "260px" }).toggle("x", "start", box);
		expect(patch).toEqual({ left: null, width: "100px" });
	});

	it("moves an auto margin's space into the side that stays, once the margins stop centring", () => {
		const centred: Box = {
			x: { ...axisBox(0, 200, 800), end: 0, marginStart: 300, marginEnd: 300 },
			y: box.y,
		};
		const pins = pinsOf({ left: "0px", right: "0px", width: "200px", margin: "0 auto" });
		expect(pins.toggle("x", "end", centred)).toMatchObject({ left: "300px", right: null });
		expect(pins.toggle("x", "start", centred)).toMatchObject({ left: null, right: "300px" });
	});

	it("leaves a content-sized block's size unset when it leaves a stretch at that size", () => {
		const text: Box = {
			x: { ...axisBox(40, 100, 400), content: 100 },
			y: { ...axisBox(20, 50, 300), content: 50 },
		};
		const pins = pinsOf({ left: "40px", right: "260px", top: "20px", bottom: "230px" });
		expect(pins.toggle("x", "end", text)).toEqual({ right: null });
		expect(pins.toggle("y", "end", text)).toEqual({ bottom: null });
		const empty: Box = { x: { ...axisBox(40, 100, 400), content: 0 }, y: box.y };
		expect(pins.toggle("x", "end", empty)).toEqual({ right: null, width: "100px" });
	});

	it("writes a new side in the unit its axis already uses", () => {
		const patch = pinsOf({ left: "10%", width: "100px" }).toggle("x", "end", box);
		expect(patch).toEqual({ right: "65%", width: null });
	});

	it("centres an axis when its only pin is dropped, offset to stay in place", () => {
		const patch = pinsOf({ right: "260px", width: "100px" }).toggle("x", "end", box);
		expect(patch).toEqual({ left: "calc(50% - 110px)", right: null, translate: "-50% 0" });
	});

	it("moves a centred axis back to a side, measured from where the block shows", () => {
		const pins = pinsOf({ left: "calc(50% - 110px)", top: "20px", width: "100px", translate: "-50% 0" });
		expect(pins.toggle("x", "start", centeredBox)).toEqual({ left: "40px", right: null, translate: null });
	});

	it("centres the second axis without losing the first", () => {
		const pins = pinsOf({ left: "50%", top: "20px", width: "100px", translate: "-50% 0" });
		expect(pins.toggleCenter("y", box)).toEqual({
			top: "calc(50% - 105px)",
			bottom: null,
			translate: "-50% -50%",
		});
	});

	it("keeps an auto width that would shrink once pinned to the narrower side", () => {
		const wide: Box = { x: axisBox(40, 300, 400), y: box.y };
		const patch = pinsOf({ left: "40px", top: "20px" }).toggleCenter("x", wide);
		expect(patch.width).toBe("300px");
	});

	it("leaves a custom translate alone", () => {
		const pins = pinsOf({ left: "40px", top: "20px", width: "100px", transform: "translate(-50%, -50%)" });
		expect(pins.toggle("x", "end", box)).toEqual({ right: "260px", width: null });
	});

	it("pins the other side, in its unit, when a custom block's only pin is dropped", () => {
		const pins = pinsOf({ left: "10%", top: "20px", width: "100px", transform: "translate(-50%, -50%)" });
		expect(pins.toggle("x", "start", box)).toEqual({ left: null, right: "65%" });
		expect(pins.setSide("top", "", box)).toEqual({ top: null, bottom: "230px" });
	});
});

describe("BlockPins on a fixed block", () => {
	const fixed = (styles: Record<string, string>) => pinsOf({ position: "fixed", ...styles });

	it("carries a vertical distance over to the side it pins, since the frame is not the window", () => {
		expect(fixed({ top: "20px", right: "20px" }).toggle("y", "end", box)).toEqual({
			bottom: "20px",
			height: null,
		});
		expect(fixed({ top: "20px", bottom: "20px" }).toggle("y", "start", box)).toEqual({ top: null });
		expect(fixed({ top: "10%" }).setSide("top", "", box)).toEqual({
			top: "50%",
			bottom: null,
			translate: "0 -50%",
		});
		expect(fixed({ top: "50%", translate: "0 -50%" }).toggle("y", "end", box)).toEqual({
			top: null,
			bottom: "0px",
			translate: null,
		});
	});

	it("still measures a horizontal side, since the frame is as wide as the window", () => {
		expect(fixed({ top: "20px", right: "260px", width: "100px" }).toggle("x", "start", box)).toEqual({
			left: "40px",
			width: null,
		});
	});
});

describe("BlockPins.setSide", () => {
	it("pins an unpinned side typed into, stretching the axis", () => {
		expect(pinsOf({ left: "40px", width: "100px" }).setSide("right", "20px", box)).toEqual({
			right: "20px",
			width: null,
		});
	});

	it("drops the centring when a side of a centred axis is typed into", () => {
		const pins = pinsOf({ left: "50%", top: "20px", translate: "-50% 0" });
		expect(pins.setSide("left", "8px", box)).toEqual({ left: "8px", right: null, translate: null });
	});

	it("unpins a side whose field is cleared or set to auto", () => {
		const stretched = pinsOf({ left: "40px", right: "260px" });
		expect(stretched.setSide("right", "", box)).toEqual({ right: null, width: "100px" });
		expect(stretched.setSide("right", "auto", box)).toEqual({ right: null, width: "100px" });
		expect(pinsOf({ left: "40px" }).setSide("right", "auto", box)).toEqual({});
	});

	it("centres the axis of a side set to center, as a centred axis's fields read", () => {
		expect(pinsOf({ left: "40px", top: "20px", width: "100px" }).setSide("right", "center", box)).toEqual({
			left: "calc(50% - 110px)",
			right: null,
			translate: "-50% 0",
		});
		expect(pinsOf({ left: "50%", translate: "-50% 0" }).setSide("left", "center", box)).toEqual({});
	});
});

describe("BlockPins.moveBy moves the pinned sides", () => {
	const shift = (px: number, percent = 0) => ({ px, percent });

	it("moves left and top for a top-left block", () => {
		expect(pinsOf({ left: "40px", top: "20px" }).moveBy(shift(20), shift(-5), box)).toEqual({
			left: "60px",
			top: "15px",
		});
	});

	it("moves right and bottom for a bottom-right block, in their own units", () => {
		const pins = pinsOf({ right: "30px", bottom: "10%" });
		expect(pins.moveBy(shift(20), shift(30, 10), box)).toEqual({ right: "10px", bottom: "0%" });
	});

	it("moves both sides of a stretched axis", () => {
		expect(pinsOf({ left: "0px", right: "0px", top: "8px" }).moveBy(shift(12), shift(0), box)).toEqual({
			left: "12px",
			right: "-12px",
		});
	});

	it("moves a centred axis by its offset and snaps back to the middle", () => {
		const pins = pinsOf({ left: "50%", top: "calc(50% + 1px)", translate: "-50% -50%" });
		expect(pins.moveBy(shift(20), shift(-1), box)).toEqual({ left: "calc(50% + 20px)", top: "50%" });
	});

	it("moves a % side in px when its container has no size", () => {
		const empty: Box = { x: axisBox(0, 40, 0), y: axisBox(0, 40, 0) };
		const pins = pinsOf({ left: "50%", top: "10%" });
		expect(pins.moveBy(shift(40, NaN), shift(30, NaN), empty)).toEqual({ left: "40px", top: "30px" });
	});

	it("pins a block with no sides at where it is", () => {
		expect(pinsOf({}).moveBy(shift(10), shift(10), box)).toEqual({ left: "50px", top: "30px" });
	});
});

describe("BlockPins.resizeBy", () => {
	const shift = (px: number) => ({ px, percent: 0 });

	it("resizes a stretched axis by its sides", () => {
		const pins = pinsOf({ left: "40px", right: "260px", top: "20px" });
		const rightHandle = pins.resizeBy({ x: shift(0), y: shift(0) }, { x: shift(30), y: shift(0) }, box);
		expect(rightHandle).toEqual({ right: "230px" });
		const leftHandle = pins.resizeBy({ x: shift(-30), y: shift(0) }, { x: shift(30), y: shift(0) }, box);
		expect(leftHandle).toEqual({ left: "10px" });
	});

	it("keeps the right side of a right-pinned block when its left handle is dragged", () => {
		const pins = pinsOf({ right: "20px", bottom: "20px" });
		const patch = pins.resizeBy({ x: shift(-30), y: shift(0) }, { x: shift(30), y: shift(0) }, box);
		expect(patch).toEqual({});
		const rightHandle = pins.resizeBy({ x: shift(0), y: shift(0) }, { x: shift(30), y: shift(0) }, box);
		expect(rightHandle).toEqual({ right: "-10px" });
	});

	it("grows a centred block around its centre", () => {
		const pins = pinsOf({ left: "50%", top: "50%", translate: "-50% -50%" });
		expect(pins.resizeBy({ x: shift(-30), y: shift(0) }, { x: shift(30), y: shift(0) }, box)).toEqual({});
	});
});

describe("BlockPins presets and clearing", () => {
	it("fills the parent", () => {
		expect(pinsOf({ left: "40px", top: "20px", width: "100px", height: "50px" }).fill()).toEqual({
			left: "0px",
			right: "0px",
			width: null,
			top: "0px",
			bottom: "0px",
			height: null,
		});
	});

	it("centres both axes", () => {
		expect(pinsOf({ left: "40px", top: "20px", width: "100px" }).center(box)).toEqual({
			left: "50%",
			right: null,
			top: "50%",
			bottom: null,
			translate: "-50% -50%",
		});
	});

	it("clears the sides and the centring", () => {
		expect(pinsOf({ left: "50%", bottom: "0px", translate: "-50% 0" }).clear()).toEqual({
			left: null,
			right: null,
			top: null,
			bottom: null,
			translate: null,
		});
	});
});
