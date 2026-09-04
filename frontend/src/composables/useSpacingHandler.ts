import type Block from "@/block";
import { CanvasProps } from "@/types/Builder/BuilderCanvas";
import type { SpacingType } from "@/utils/cssUtils";
import {
	SPACING_PROPERTIES,
	collapseBoxShorthand,
	collapseGapShorthand,
	expandBoxShorthand,
	expandGapShorthand,
} from "@/utils/cssUtils";
import { startDrag } from "@/utils/cursor";
import { getNumberFromPx } from "@/utils/helpers";
import { toLocalDelta } from "@/utils/rotation";
import { clamp } from "@vueuse/core";
import { computed, inject, ref } from "vue";

export enum Position {
	Top = "top",
	Right = "right",
	Bottom = "bottom",
	Left = "left",
}

type SpacingDragOptions = {
	property: SpacingType;
	// the value to grow from when the side has none set yet
	fallback: number;
	getRotation: () => number;
	onUpdate?: () => void;
};

// `outward` is the sign of a drag pointing away from the block along the side's axis.
const sides = {
	[Position.Top]: { axis: "y", outward: -1, index: 0 },
	[Position.Right]: { axis: "x", outward: 1, index: 1 },
	[Position.Bottom]: { axis: "y", outward: 1, index: 2 },
	[Position.Left]: { axis: "x", outward: -1, index: 3 },
} as const;

const verticalSides = [Position.Top, Position.Bottom];
const horizontalSides = [Position.Left, Position.Right];
const allSides = [...verticalSides, ...horizontalSides];

// margin/padding spread over four box sides, gap over two axes. Only the shorthand
// shape differs, so each property just says how to expand and collapse its own.
type ShorthandCodec = {
	expand: (value: unknown) => string[];
	collapse: (parts: unknown[]) => string;
};

const shorthandCodec = (property: SpacingType): ShorthandCodec =>
	SPACING_PROPERTIES[property].slots === 4
		? { expand: expandBoxShorthand, collapse: collapseBoxShorthand }
		: { expand: expandGapShorthand, collapse: collapseGapShorthand };

// A gap has no sides — its two slots are the row (y) and column (x) axes — so both
// handles on an axis address the same slot.
const slotIndex = (property: SpacingType, side: Position) =>
	SPACING_PROPERTIES[property].slots === 4 ? sides[side].index : sides[side].axis === "y" ? 0 : 1;

// Shared state and drag behaviour for the Margin, Padding and Gap handlers. The
// per-slot positioning and value display differ and stay in each component.
export function useSpacingHandler(getTargetBlock: () => Block, getBreakpoint: () => string) {
	const canvasProps = inject("canvasProps") as CanvasProps;
	const updating = ref(false);

	const blockStyles = computed(() => {
		const breakpoint = getBreakpoint();
		let styles = { ...getTargetBlock().baseStyles };
		if (breakpoint === "mobile" || breakpoint === "tablet") {
			styles = { ...styles, ...getTargetBlock().mobileStyles };
		}
		if (breakpoint === "tablet") {
			styles = { ...styles, ...getTargetBlock().tabletStyles };
		}
		return styles;
	});

	const handleBorderWidth = computed(() => `${clamp(1 * canvasProps.scale, 1, 2)}px`);

	// Long-edge handles (top/bottom, and the horizontal row-gap bands) are wide and
	// short; side handles (left/right, and the vertical column-gap bands) are tall and
	// narrow. The dimensions are identical for all three properties; only the offsets
	// (set per-component) differ.
	const longHandleSize = computed(() => ({
		width: clamp(16 * canvasProps.scale, 8, 32),
		height: clamp(4 * canvasProps.scale, 2, 8),
	}));
	const sideHandleSize = computed(() => ({
		width: clamp(4 * canvasProps.scale, 2, 8),
		height: clamp(16 * canvasProps.scale, 8, 32),
	}));

	const styleKey = (property: SpacingType, side: Position) =>
		SPACING_PROPERTIES[property].longhands[slotIndex(property, side)];

	// Slot-specific spacing styles (paddingTop, rowGap, …) are legacy data. Read them
	// for display/editing, then collapse every update back into the single shorthand.
	const getSpacingParts = (property: SpacingType) => {
		const styles = blockStyles.value;
		const parts = shorthandCodec(property).expand(styles[property] ?? "");
		allSides.forEach((side) => {
			const sideValue = styles[styleKey(property, side)];
			if (sideValue) parts[slotIndex(property, side)] = String(sideValue);
		});
		return parts;
	};

	const getSpacingValue = (property: SpacingType, side: Position) =>
		getSpacingParts(property)[slotIndex(property, side)];

	const setSpacingShorthand = (property: SpacingType, updatedSides: Position[], value: number) => {
		const block = getTargetBlock();
		const parts = getSpacingParts(property);
		updatedSides.forEach((updatedSide) => {
			parts[slotIndex(property, updatedSide)] = `${value}px`;
		});
		SPACING_PROPERTIES[property].longhands.forEach((longhand) => block.setStyle(longhand, null));
		block.setStyle(property, shorthandCodec(property).collapse(parts));
	};

	// Shift spreads the value to every slot (four box sides, or both gap axes), alt to
	// both sides of the dragged axis — which for a gap is the dragged axis itself.
	const sidesToUpdate = (event: MouseEvent, side: Position) => {
		if (event.shiftKey) return allSides;
		if (event.altKey) return sides[side].axis === "y" ? verticalSides : horizontalSides;
		return [side];
	};

	const startSpacingDrag = (
		event: MouseEvent,
		side: Position,
		{ property, fallback, getRotation, onUpdate }: SpacingDragOptions,
	) => {
		const { axis, outward } = sides[side];
		// the handles sit on the block's edge, so dragging outward grows a margin but shrinks a
		// padding. A gap handle sits in the gap itself, where outward simply widens it.
		const sign = property === "padding" ? -outward : outward;
		const startValue = getNumberFromPx(getSpacingValue(property, side)) || fallback;
		const startPoint = { x: event.clientX, y: event.clientY };

		event.preventDefault();
		updating.value = true;

		startDrag({
			cursor: window.getComputedStyle(event.target as HTMLElement).cursor,
			onMove: (moveEvent) => {
				onUpdate?.();
				const delta = toLocalDelta(
					moveEvent.clientX - startPoint.x,
					moveEvent.clientY - startPoint.y,
					getRotation(),
				);
				const value = Math.round(Math.max(startValue + sign * delta[axis], 0));
				setSpacingShorthand(property, sidesToUpdate(moveEvent, side), value);
			},
			onEnd: () => {
				updating.value = false;
			},
		});
	};

	return {
		canvasProps,
		updating,
		blockStyles,
		handleBorderWidth,
		longHandleSize,
		sideHandleSize,
		getSpacingValue,
		startSpacingDrag,
	};
}
