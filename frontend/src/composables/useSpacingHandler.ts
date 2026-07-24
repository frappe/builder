import type Block from "@/block";
import { CanvasProps } from "@/types/Builder/BuilderCanvas";
import { collapseBoxShorthand, expandBoxShorthand } from "@/utils/cssUtils";
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

type SpacingProperty = "margin" | "padding";

type SpacingDragOptions = {
	property: SpacingProperty;
	// the value to grow from when the side has none set yet
	fallback: number;
	getRotation: () => number;
	onUpdate?: () => void;
};

// `outward` is the sign of a drag pointing away from the block along the side's axis.
const sides = {
	[Position.Top]: { axis: "y", outward: -1, styleSuffix: "Top", index: 0 },
	[Position.Right]: { axis: "x", outward: 1, styleSuffix: "Right", index: 1 },
	[Position.Bottom]: { axis: "y", outward: 1, styleSuffix: "Bottom", index: 2 },
	[Position.Left]: { axis: "x", outward: -1, styleSuffix: "Left", index: 3 },
} as const;

const verticalSides = [Position.Top, Position.Bottom];
const horizontalSides = [Position.Left, Position.Right];
const allSides = [...verticalSides, ...horizontalSides];

// Shared state and drag behaviour for the Margin and Padding handlers. The per-side
// positioning and value display differ and stay in each component.
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

	// Long-edge handles (top/bottom) are wide and short; side handles (left/right)
	// are tall and narrow. The dimensions are identical for margin and padding;
	// only the offsets (set per-component) differ.
	const longHandleSize = computed(() => ({
		width: clamp(16 * canvasProps.scale, 8, 32),
		height: clamp(4 * canvasProps.scale, 2, 8),
	}));
	const sideHandleSize = computed(() => ({
		width: clamp(4 * canvasProps.scale, 2, 8),
		height: clamp(16 * canvasProps.scale, 8, 32),
	}));

	const styleKey = (property: SpacingProperty, side: Position) =>
		`${property}${sides[side].styleSuffix}` as styleProperty;

	// Side-specific spacing styles are legacy data. Read them for display/editing,
	// then collapse every update back into the single shorthand style.
	const getSpacingParts = (property: SpacingProperty) => {
		const styles = blockStyles.value;
		const parts = expandBoxShorthand(styles[property] ?? "", "0px");
		allSides.forEach((side) => {
			const sideValue = styles[styleKey(property, side)];
			if (sideValue) parts[sides[side].index] = String(sideValue);
		});
		return parts;
	};

	const getSpacingValue = (property: SpacingProperty, side: Position) =>
		getSpacingParts(property)[sides[side].index];

	const setSpacingShorthand = (property: SpacingProperty, updatedSides: Position[], value: number) => {
		const block = getTargetBlock();
		const parts = getSpacingParts(property);
		updatedSides.forEach((updatedSide) => {
			parts[sides[updatedSide].index] = `${value}px`;
		});
		block.setStyle(`${property}Top`, null);
		block.setStyle(`${property}Right`, null);
		block.setStyle(`${property}Bottom`, null);
		block.setStyle(`${property}Left`, null);
		block.setStyle(property, collapseBoxShorthand(parts));
	};

	// Shift spreads the value to all four sides, alt to both sides of the dragged axis.
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
		// the handles sit on the block's edge, so dragging outward grows a margin but shrinks a padding
		const sign = property === "margin" ? outward : -outward;
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
