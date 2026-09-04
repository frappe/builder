<template>
	<div
		class="group"
		:class="{
			'opacity-40': !updating,
			'opacity-70': updating,
		}"
		@click.stop>
		<div
			v-for="band in gapBands"
			:key="band.key"
			class="gap-handler pointer-events-none absolute z-10 flex bg-purple-400"
			:style="band.style">
			<div
				v-show="canvasProps.scale > HANDLE_MIN_SCALE"
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				:class="{ hidden: updating }"
				:style="band.handleStyle"
				@mousedown.stop="handleGap($event, band.position)" />
			<div v-show="updating" class="m-auto text-sm text-purple-900">
				{{ getGapValue(band.position) }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { useRotatedCursors } from "@/composables/useRotatedCursors";
import { Position, useSpacingHandler } from "@/composables/useSpacingHandler";
import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from "vue";
import { getNumberFromPx } from "../utils/helpers";

const props = withDefaults(
	defineProps<{
		targetBlock: Block;
		disableHandlers?: boolean;
		onUpdate?: () => void;
		breakpoint?: string;
		target: HTMLElement | SVGElement;
	}>(),
	{
		disableHandlers: false,
		breakpoint: "desktop",
		onUpdate: undefined,
	},
);

const emit = defineEmits(["update"]);
const {
	canvasProps,
	updating,
	blockStyles,
	getSpacingValue,
	handleBorderWidth,
	longHandleSize,
	sideHandleSize,
	startSpacingDrag,
} = useSpacingHandler(
	() => props.targetBlock,
	() => props.breakpoint,
);

watchEffect(() => {
	emit("update", updating.value);
});

const { rotation, horizontalCursor, verticalCursor } = useRotatedCursors(
	() => props.target as Element,
	() => props.targetBlock,
);

const CHILD_SELECTOR = ":scope > .__builder_component__";

// Below this zoom the handles are smaller than they are grabbable, so hide them.
const HANDLE_MIN_SCALE = 0.5;

// A zero gap measures as a zero-thickness band, which would leave nothing on screen to aim
// at. Paint it this thick (in canvas pixels) so the seam — and the handle sitting on it —
// stays findable, exactly as a padding handle stays visible at zero padding.
const MIN_BAND = 2;

// Any of these moves the children, and with them the seams the bands are drawn on.
const LAYOUT_STYLES = [
	"gap",
	"rowGap",
	"columnGap",
	"display",
	"flexDirection",
	"flexWrap",
	"padding",
	"gridTemplateColumns",
	"gridTemplateRows",
] as const;

// A box in the block's own (unscaled, unrotated) layout space, measured from the top-left
// of its border box — the same origin the editor host is anchored to.
type Box = { x0: number; y0: number; x1: number; y1: number };
// One drawn overlay: the painted strip plus the pill that drags it, both already in canvas
// pixels relative to the editor host.
type GapBand = {
	key: string;
	position: Position;
	style: Record<string, string>;
	handleStyle: Record<string, string | undefined>;
};

// Child geometry isn't reactive: a child resizing, or the block reflowing after its own
// first paint, moves the seams without touching any style this component reads. Bumping
// this on every observed resize re-runs the measurement.
const measured = ref(0);
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
	const target = props.target as HTMLElement;
	if (!target || typeof ResizeObserver === "undefined") return;
	resizeObserver = new ResizeObserver(() => measured.value++);
	resizeObserver.observe(target);
	target.querySelectorAll(CHILD_SELECTOR).forEach((child) => resizeObserver?.observe(child));
});

onBeforeUnmount(() => {
	resizeObserver?.disconnect();
	resizeObserver = null;
});

// offsetLeft/offsetTop are layout coordinates, so — unlike getBoundingClientRect — they
// stay correct when the block, and with it the editor host, is rotated.
const layoutOffset = (el: HTMLElement) => {
	let x = 0;
	let y = 0;
	let node: HTMLElement | null = el;
	while (node) {
		x += node.offsetLeft;
		y += node.offsetTop;
		node = node.offsetParent as HTMLElement | null;
	}
	return { x, y };
};

// Position of a child's border box within the target's, which is the origin the editor host
// is anchored to. Summing each chain to the root and subtracting cancels whatever they
// share, but an offset is measured from its offsetParent's *padding* edge: when that
// offsetParent is the target itself, its border has to be added back. When the target isn't
// positioned the chain skips it, both are measured from the same ancestor, and the
// difference already is border box to border box.
const offsetWithin = (child: HTMLElement, target: HTMLElement, targetOffset: { x: number; y: number }) => {
	const { x, y } = layoutOffset(child);
	const nested = child.offsetParent === target;
	return {
		x: x - targetOffset.x + (nested ? target.clientLeft : 0),
		y: y - targetOffset.y + (nested ? target.clientTop : 0),
	};
};

const topOf = (line: Box[]) => Math.min(...line.map((box) => box.y0));
const bottomOf = (line: Box[]) => Math.max(...line.map((box) => box.y1));

// Two children share a visual line when they overlap vertically by more than half of the
// shorter one — robust to ragged item heights in a wrapped flex or a grid.
const sameLine = (a: Box, b: Box) => {
	const overlap = Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0);
	const shorter = Math.min(a.y1 - a.y0, b.y1 - b.y0) || 1;
	return overlap > shorter * 0.5;
};

// Group the children into visual lines: one line per grid/wrap row, a single line for a
// flex row, one line per child for a flex column. Grouping is purely geometric — a box
// joins the first line it shares a band with — because DOM order is not visual order:
// `order` on a flex child, and grid auto-placement, both move a child between rows without
// moving it in the DOM. Lines and their contents come back in visual order, top-to-bottom
// then left-to-right. Never emits an empty line.
const clusterLines = (boxes: Box[]) => {
	const lines: Box[][] = [];
	[...boxes]
		.sort((a, b) => a.y0 - b.y0 || a.x0 - b.x0)
		.forEach((box) => {
			const line = lines.find((candidate) => candidate.some((sibling) => sameLine(sibling, box)));
			if (line) line.push(box);
			else lines.push([box]);
		});
	lines.forEach((line) => line.sort((a, b) => a.x0 - b.x0));
	return lines.sort((a, b) => topOf(a) - topOf(b));
};

const layout = computed(() => {
	// read the styles that move the children, so the bands re-measure on each edit
	LAYOUT_STYLES.forEach((property) => void blockStyles.value[property]);
	void props.targetBlock.getChildren().length;
	void measured.value;

	const target = props.target as HTMLElement;
	if (!target?.isConnected) return null;

	const style = getComputedStyle(target);
	// Decide off the rendered display, not the block's own styles: a block laid out by a CSS
	// class rather than an inline style is still a flex/grid container, and gap only applies
	// to those two.
	if (!/^(inline-)?(flex|grid)$/.test(style.display)) return null;

	const targetOffset = layoutOffset(target);
	const builderChildren = Array.from(target.querySelectorAll(CHILD_SELECTOR)) as HTMLElement[];
	const children =
		builderChildren.length >= 2 ? builderChildren : (Array.from(target.children) as HTMLElement[]);

	const boxes: Box[] = [];
	children.forEach((child) => {
		if (child.id === "placeholder") return;
		// a hidden child has no box, which also covers display:none
		if (!child.offsetWidth && !child.offsetHeight) return;
		const { x, y } = offsetWithin(child, target, targetOffset);
		boxes.push({ x0: x, y0: y, x1: x + child.offsetWidth, y1: y + child.offsetHeight });
	});
	if (boxes.length < 2) return null;

	return {
		lines: clusterLines(boxes),
		content: {
			x0: target.clientLeft + getNumberFromPx(style.paddingLeft),
			y0: target.clientTop + getNumberFromPx(style.paddingTop),
			x1: target.clientLeft + target.clientWidth - getNumberFromPx(style.paddingRight),
			y1: target.clientTop + target.clientHeight - getNumberFromPx(style.paddingBottom),
		} as Box,
	};
});

// Scale a band into canvas pixels, then keep it at least MIN_BAND thick across the axis it
// straddles, centred so it still sits over the real seam.
const bandStyle = (band: Box, axis: "width" | "height") => {
	const left = band.x0 * canvasProps.scale;
	const top = band.y0 * canvasProps.scale;
	const width = (band.x1 - band.x0) * canvasProps.scale;
	const height = (band.y1 - band.y0) * canvasProps.scale;
	const thickness = Math.max(axis === "width" ? width : height, MIN_BAND);
	const shift = (thickness - (axis === "width" ? width : height)) / 2;

	return axis === "width"
		? { left: `${left - shift}px`, top: `${top}px`, width: `${thickness}px`, height: `${height}px` }
		: { left: `${left}px`, top: `${top - shift}px`, width: `${width}px`, height: `${thickness}px` };
};

// `place` is where the pill sits inside its band: centred across the thin axis so it
// straddles the seam and stays grabbable at a zero gap, anchored along the long one.
const handleStyle = (
	size: { width: number; height: number },
	place: { left: string; top: string },
	cursor: string,
) => ({
	borderWidth: handleBorderWidth.value,
	left: place.left,
	top: place.top,
	width: `${size.width}px`,
	height: `${size.height}px`,
	cursor: props.disableHandlers ? undefined : cursor,
});

// One band per column boundary, spanning the full content height. Every line shares the
// same column-gap, so the fullest line carries all of the boundaries.
const columnBands = (lines: Box[][], content: Box): GapBand[] => {
	const widest = lines.reduce((longest, line) => (line.length > longest.length ? line : longest));
	const size = sideHandleSize.value;
	// A band spans the whole content height, so centring the grab point in it would push the
	// handle off-screen on a tall container. Sit it on the row these seams came from.
	const centerY = ((topOf(widest) + bottomOf(widest)) / 2 - content.y0) * canvasProps.scale;

	return widest.slice(1).map((box, index) => {
		const x0 = widest[index].x1;
		// offsets are whole pixels, so a zero gap can measure slightly negative — clamp
		// rather than skip, or the seam would never get a handle
		const x1 = Math.max(box.x0, x0);
		return {
			key: `column-${index}`,
			position: Position.Right,
			style: bandStyle({ x0, x1, y0: content.y0, y1: content.y1 }, "width"),
			handleStyle: handleStyle(
				size,
				{ left: `calc(50% - ${size.width / 2}px)`, top: `${centerY - size.height / 2}px` },
				horizontalCursor.value,
			),
		};
	});
};

// One band per line boundary, spanning the full content width.
const rowBands = (lines: Box[][], content: Box): GapBand[] => {
	const size = longHandleSize.value;

	return lines.slice(1).map((line, index) => {
		const previous = lines[index];
		const y0 = bottomOf(previous);
		const y1 = Math.max(topOf(line), y0);

		return {
			key: `row-${index}`,
			position: Position.Bottom,
			style: bandStyle({ x0: content.x0, x1: content.x1, y0, y1 }, "height"),
			handleStyle: handleStyle(
				size,
				{ left: `calc(50% - ${size.width / 2}px)`, top: `calc(50% - ${size.height / 2}px)` },
				verticalCursor.value,
			),
		};
	});
};

const gapBands = computed<GapBand[]>(() => {
	if (!layout.value) return [];
	const { lines, content } = layout.value;
	return [...columnBands(lines, content), ...rowBands(lines, content)];
});

const getGapValue = (position: Position) => getSpacingValue("gap", position);

const handleGap = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	startSpacingDrag(ev, position, {
		property: "gap",
		fallback: 0,
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
