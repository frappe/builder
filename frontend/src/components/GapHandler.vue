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
			class="gap-handler absolute z-10 flex"
			:class="[
				band.draggable && !disableHandlers ? 'pointer-events-auto' : 'pointer-events-none',
				{ 'bg-purple-300': band.filled && isActive(band.key) },
			]"
			:style="band.style"
			@mouseenter="hoveredBand = band.key"
			@mouseleave="hoveredBand = null"
			@mousedown.stop="handleGap($event, band)">
			<div
				v-show="canvasProps.scale > HANDLE_MIN_SCALE"
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				:class="{ hidden: updating }"
				:style="band.handleStyle"
				@mousedown.stop="handleGap($event, band)" />
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

// A band is filled only while it or its pill is hovered, or it is being dragged.
const hoveredBand = ref<string | null>(null);
const draggedBand = ref<string | null>(null);
const isActive = (key: string) => (updating.value ? draggedBand.value : hoveredBand.value) === key;

const { rotation, horizontalCursor, verticalCursor } = useRotatedCursors(
	() => props.target as Element,
	() => props.targetBlock,
);

const CHILD_SELECTOR = ":scope > .__builder_component__";
const HANDLE_MIN_SCALE = 0.5;
const MIN_BAND = 2;
const MIN_DRAGGABLE_BAND = 8;

// Changing any of these moves the children, so the bands have to be measured again.
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

type Box = { x0: number; y0: number; x1: number; y1: number };
type Span = { y0: number; y1: number };
// A gap to put a band on: where it starts and ends along one axis.
type Seam = { from: number; to: number };
type GapBand = {
	key: string;
	position: Position;
	draggable: boolean;
	filled: boolean;
	style: Record<string, string | undefined>;
	handleStyle: Record<string, string | undefined>;
};

// A resize moves the children without changing a style, so watch for it and measure again.
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

// Two children are on the same line if they overlap by more than half the shorter one.
const sameLine = (a: Span, b: Span) => {
	const overlap = Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0);
	const shorter = Math.min(a.y1 - a.y0, b.y1 - b.y0) || 1;
	return overlap > shorter * 0.5;
};

const clusterLines = (boxes: Box[]) => {
	const lines: { boxes: Box[]; band: Span }[] = [];
	[...boxes]
		.sort((a, b) => a.y0 - b.y0 || a.x0 - b.x0)
		.forEach((box) => {
			const line = lines.find((candidate) => sameLine(candidate.band, box));
			if (!line) {
				lines.push({ boxes: [box], band: { y0: box.y0, y1: box.y1 } });
				return;
			}
			line.boxes.push(box);
			line.band = { y0: Math.max(line.band.y0, box.y0), y1: Math.min(line.band.y1, box.y1) };
		});
	const grouped = lines.map(({ boxes }) => boxes.sort((a, b) => a.x0 - b.x0));
	return grouped.sort((a, b) => topOf(a) - topOf(b));
};

const layout = computed(() => {
	LAYOUT_STYLES.forEach((property) => void blockStyles.value[property]);
	void props.targetBlock.getChildren().length;
	void measured.value;

	const target = props.target as HTMLElement;
	if (!target?.isConnected) return null;

	const style = getComputedStyle(target);
	if (!/^(inline-)?(flex|grid)$/.test(style.display)) return null;

	const targetOffset = layoutOffset(target);
	const builderChildren = Array.from(target.querySelectorAll(CHILD_SELECTOR)) as HTMLElement[];
	const children =
		builderChildren.length >= 2 ? builderChildren : (Array.from(target.children) as HTMLElement[]);

	const boxes: Box[] = [];
	children.forEach((child) => {
		if (child.id === "placeholder") return;
		if (!child.offsetWidth && !child.offsetHeight) return;
		const { x, y } = offsetWithin(child, target, targetOffset);
		boxes.push({ x0: x, y0: y, x1: x + child.offsetWidth, y1: y + child.offsetHeight });
	});
	if (boxes.length < 2) return null;

	return {
		lines: clusterLines(boxes),
		tracks: { column: style.gridTemplateColumns, row: style.gridTemplateRows },
		reach: {
			column: { from: Math.min(...boxes.map((b) => b.x0)), to: Math.max(...boxes.map((b) => b.x1)) },
			row: { from: Math.min(...boxes.map((b) => b.y0)), to: Math.max(...boxes.map((b) => b.y1)) },
		},
		gap: {
			column: getNumberFromPx(style.columnGap),
			row: getNumberFromPx(style.rowGap),
		},
		content: {
			x0: target.clientLeft + getNumberFromPx(style.paddingLeft),
			y0: target.clientTop + getNumberFromPx(style.paddingTop),
			x1: target.clientLeft + target.clientWidth - getNumberFromPx(style.paddingRight),
			y1: target.clientTop + target.clientHeight - getNumberFromPx(style.paddingBottom),
		} as Box,
	};
});

// Turn a band into canvas pixels, kept thick enough to see and centred on the real seam.
const bandStyle = (band: Box, axis: "width" | "height", cursor?: string) => {
	const left = band.x0 * canvasProps.scale;
	const top = band.y0 * canvasProps.scale;
	const width = (band.x1 - band.x0) * canvasProps.scale;
	const height = (band.y1 - band.y0) * canvasProps.scale;
	const thickness = Math.max(axis === "width" ? width : height, MIN_BAND);
	const shift = (thickness - (axis === "width" ? width : height)) / 2;

	const box =
		axis === "width"
			? { left: `${left - shift}px`, top: `${top}px`, width: `${thickness}px`, height: `${height}px` }
			: { left: `${left}px`, top: `${top - shift}px`, width: `${width}px`, height: `${thickness}px` };
	return { ...box, cursor: props.disableHandlers ? undefined : cursor };
};

const isDraggable = (gap: number) => gap * canvasProps.scale >= MIN_DRAGGABLE_BAND;

const handleStyle = (
	size: { width: number; height: number },
	cursor: string,
	top = `calc(50% - ${size.height / 2}px)`,
) => ({
	borderWidth: handleBorderWidth.value,
	left: `calc(50% - ${size.width / 2}px)`,
	top,
	width: `${size.width}px`,
	height: `${size.height}px`,
	cursor: props.disableHandlers ? undefined : cursor,
});

// A grid's tracks come back in pixels, so its seams are exact even where an item spans rows or
// a cell is empty and the children show nothing.
const trackSeams = (template: string, start: number, gap: number, reach: Seam): Seam[] | null => {
	const sizes = template.match(/-?[\d.]+px/g);
	if (!sizes || sizes.length < 2) return null;

	let edge = start;
	const seams = sizes.slice(0, -1).map((size) => {
		edge += getNumberFromPx(size) + gap;
		return { from: edge - gap, to: edge };
	});
	// auto-fill can leave tracks the children never reach, and those seams sit between nothing.
	return seams.filter((seam) => seam.from >= reach.from && seam.to <= reach.to);
};

// One seam per column boundary, taken from the line with the most children.
const columnSeams = (lines: Box[][]): Seam[] => {
	const widest = lines.reduce((longest, line) => (line.length > longest.length ? line : longest));
	return widest.slice(1).map((box, index) => {
		const from = widest[index].x1;
		return { from, to: Math.max(box.x0, from) };
	});
};

// One seam per boundary between lines.
const rowSeams = (lines: Box[][]): Seam[] =>
	lines.slice(1).map((line, index) => {
		// A tall item crosses the seam, so measure the gap from the lowest item that stops above it.
		const above = lines[index].filter((box) => !line.some((sibling) => sameLine(box, sibling)));
		const from = above.length ? bottomOf(above) : topOf(line);
		return { from, to: Math.max(topOf(line), from) };
	});

// Middle of the row line at the content's centre, or the line above when the centre is a row gap —
// a row band there would paint over the column pill.
const columnPillY = (rows: Seam[], content: Box) => {
	const middle = (content.y0 + content.y1) / 2;
	const tops = [content.y0, ...rows.map((seam) => seam.to)];
	const bottoms = [...rows.map((seam) => seam.from), content.y1];
	const line = tops.findLastIndex((top) => top <= middle);
	return (tops[line] + bottoms[line]) / 2;
};

// One band per seam, spanning the full content height.
const columnBands = (seams: Seam[], content: Box, gap: number, pillY: number): GapBand[] =>
	seams.map((seam, index) => {
		const draggable = isDraggable(seam.to - seam.from);
		const size = sideHandleSize.value;
		return {
			key: `column-${index}`,
			position: Position.Right,
			draggable,
			filled: gap > 0,
			style: bandStyle(
				{ x0: seam.from, x1: seam.to, y0: content.y0, y1: content.y1 },
				"width",
				draggable ? horizontalCursor.value : undefined,
			),
			handleStyle: handleStyle(
				size,
				horizontalCursor.value,
				`${(pillY - content.y0) * canvasProps.scale - size.height / 2}px`,
			),
		};
	});

// One band per seam, across the full content width.
const rowBands = (seams: Seam[], content: Box, gap: number): GapBand[] =>
	seams.map((seam, index) => {
		const draggable = isDraggable(seam.to - seam.from);
		return {
			key: `row-${index}`,
			position: Position.Bottom,
			draggable,
			filled: gap > 0,
			style: bandStyle(
				{ x0: content.x0, x1: content.x1, y0: seam.from, y1: seam.to },
				"height",
				draggable ? verticalCursor.value : undefined,
			),
			handleStyle: handleStyle(longHandleSize.value, verticalCursor.value),
		};
	});

const gapBands = computed<GapBand[]>(() => {
	if (!layout.value) return [];
	const { lines, content, gap, tracks, reach } = layout.value;
	const columns = trackSeams(tracks.column, content.x0, gap.column, reach.column) ?? columnSeams(lines);
	const rows = trackSeams(tracks.row, content.y0, gap.row, reach.row) ?? rowSeams(lines);
	return [
		...columnBands(columns, content, gap.column, columnPillY(rows, content)),
		...rowBands(rows, content, gap.row),
	];
});

const getGapValue = (position: Position) => getSpacingValue("gap", position);

const handleGap = (ev: MouseEvent, band: GapBand) => {
	if (props.disableHandlers) return;
	draggedBand.value = band.key;
	hoveredBand.value = null;
	startSpacingDrag(ev, band.position, {
		property: "gap",
		fallback: 0,
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
