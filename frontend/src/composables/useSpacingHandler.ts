import type Block from "@/block";
import { CanvasProps } from "@/types/Builder/BuilderCanvas";
import { clamp } from "@vueuse/core";
import { computed, inject, ref } from "vue";

export enum Position {
	Top = "top",
	Right = "right",
	Bottom = "bottom",
	Left = "left",
}

// Shared state and derivations for the Margin and Padding drag handlers. Only
// the pieces that are byte-for-byte identical between the two live here; the
// per-side positioning, drag direction, defaults and value display differ and
// stay in each component.
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

	return { canvasProps, updating, blockStyles, handleBorderWidth, longHandleSize, sideHandleSize };
}
