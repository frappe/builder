import { beforeEach, describe, expect, it, vi } from "vitest";

const block = { activeState: null as string | null };
vi.mock("@/utils/blockController", () => ({
	default: { getSelectedBlocks: () => [block] },
}));

// the composable listens on the document for the presses that show user intent
globalThis.document = new EventTarget() as unknown as Document;

const frames: FrameRequestCallback[] = [];
globalThis.requestAnimationFrame = ((callback: FrameRequestCallback) =>
	frames.push(callback)) as typeof requestAnimationFrame;
const runFrame = () => frames.splice(0).forEach((callback) => callback(0));

import { useStatePopover } from "./useStatePopover";

const createPopover = () => {
	const popover = {
		isOpen: false,
		toggle: (open: boolean) => (popover.isOpen = open),
	};
	return popover;
};

type Popover = ReturnType<typeof createPopover>;
type StatePopover = ReturnType<typeof useStatePopover>;

const clickSwatch = (popover: Popover, statePopover: StatePopover, state: string | null) => {
	document.dispatchEvent(new Event("pointerdown"));
	statePopover.rememberPopoverState(state, popover.isOpen);
	statePopover.togglePopoverForState(state, popover.toggle);
};

// a state row takes focus back when the panel closes, to keep its preview
const reclaimFocus = (popover: Popover, statePopover: StatePopover) => {
	if (statePopover.canOpenOnFocus()) popover.toggle(true);
};

// canvas handles prevent their own mousedown
const dragCanvasHandle = () => {
	const press = new Event("mousedown", { cancelable: true });
	document.addEventListener("mousedown", () => press.preventDefault(), { once: true });
	document.dispatchEvent(press);
};

describe("useStatePopover", () => {
	beforeEach(() => (block.activeState = "hover:background"));

	it("opens on the first swatch click and closes on the second", () => {
		const popover = createPopover();
		const statePopover = useStatePopover();

		clickSwatch(popover, statePopover, "hover");
		expect(popover.isOpen).toBe(true);

		clickSwatch(popover, statePopover, "hover");
		expect(popover.isOpen).toBe(false);
	});

	it("stays open when the swatch of another state is clicked", () => {
		const popover = createPopover();
		const statePopover = useStatePopover();

		clickSwatch(popover, statePopover, "hover");
		clickSwatch(popover, statePopover, "focus");

		expect(popover.isOpen).toBe(true);
		expect(statePopover.activeState.value).toBe("focus");
	});

	it("keeps the popover closed when the row reclaims focus", () => {
		const popover = createPopover();
		const statePopover = useStatePopover();

		clickSwatch(popover, statePopover, "hover");
		clickSwatch(popover, statePopover, "hover");
		reclaimFocus(popover, statePopover);

		expect(popover.isOpen).toBe(false);
	});

	it("opens on focus again after the user presses or types", () => {
		const popover = createPopover();
		const statePopover = useStatePopover();

		clickSwatch(popover, statePopover, "hover");
		clickSwatch(popover, statePopover, "hover");
		document.dispatchEvent(new Event("keydown"));
		reclaimFocus(popover, statePopover);

		expect(popover.isOpen).toBe(true);
	});

	it("ends the state preview on the block", () => {
		useStatePopover().endStatePreview();
		runFrame();

		expect(block.activeState).toBe(null);
	});

	it("keeps the state preview when a canvas handle takes over", () => {
		useStatePopover().endStatePreview();
		dragCanvasHandle();
		runFrame();

		expect(block.activeState).toBe("hover:background");
	});

	it("keeps the state preview when another control takes over the state", () => {
		useStatePopover().endStatePreview();
		block.activeState = "focus:background";
		runFrame();

		expect(block.activeState).toBe("focus:background");
	});
});
