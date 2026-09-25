<template>
	<div class="group" @click.stop>
		<CursorTooltip v-if="updating" purple :position="cursorPosition">
			{{ getGapValue(activeSides[0]) }}
		</CursorTooltip>
		<!-- clipped to stay inside the 2px selection ring, which is drawn under the bands -->
		<div class="pointer-events-none absolute inset-0 opacity-30 [clip-path:inset(2px)]">
			<div
				v-for="band in gapBands"
				v-show="band.filled && isActive(band.position)"
				:key="band.key"
				class="absolute bg-purple-400"
				:style="band.style" />
		</div>
		<div
			v-for="band in gapBands"
			:key="band.key"
			class="gap-handler absolute z-10 flex"
			:class="band.draggable && !disableHandlers ? 'pointer-events-auto' : 'pointer-events-none'"
			:style="band.style"
			@mousedown.stop="handleGap($event, band)">
			<div
				v-show="showPill"
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-400 bg-purple-300 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				:class="{ hidden: updating }"
				:style="band.handleStyle" />
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { useRotatedCursors } from "@/composables/useRotatedCursors";
import { HANDLE_MIN_SCALE, Position, useSpacingHandler } from "@/composables/useSpacingHandler";
import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from "vue";
import { getNumberFromPx } from "../utils/helpers";
import CursorTooltip from "./CursorTooltip.vue";

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
	activeSides,
	cursorPosition,
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

const isActive = (position: Position) => updating.value && activeSides.value.includes(position);

const { rotation, horizontalCursor, verticalCursor } = useRotatedCursors(
	() => props.target as Element,
	() => props.targetBlock,
);

const CHILD_SELECTOR = ":scope > .__builder_component__";
const MIN_BAND = 2;
const MIN_DRAGGABLE_BAND = 8;

const showPill = computed(() => canvasProps.scale > HANDLE_MIN_SCALE);

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
	"justifyContent",
	"alignContent",
] as const;

type Box = { x0: number; y0: number; x1: number; y1: number };
type Span = { y0: number; y1: number };
// A gap to put a band on: where it starts and ends along one axis.
type Seam = { from: number; to: number };
type Track = { template: string; align: string };
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
		tracks: {
			column: { template: style.gridTemplateColumns, align: style.justifyContent },
			row: { template: style.gridTemplateRows, align: style.alignContent },
		},
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
	const thickness = Math.max(
		axis === "width" ? width : height,
		showPill.value ? MIN_BAND : MIN_DRAGGABLE_BAND,
	);
	const shift = (thickness - (axis === "width" ? width : height)) / 2;

	const box =
		axis === "width"
			? { left: `${left - shift}px`, top: `${top}px`, width: `${thickness}px`, height: `${height}px` }
			: { left: `${left}px`, top: `${top - shift}px`, width: `${width}px`, height: `${thickness}px` };
	return { ...box, cursor: props.disableHandlers ? undefined : cursor };
};

const isDraggable = (gap: number) => !showPill.value || gap * canvasProps.scale >= MIN_DRAGGABLE_BAND;

const handleStyle = (size: { width: number; height: number }, cursor: string, centreY?: number) => ({
	borderWidth: handleBorderWidth.value,
	left: `calc(50% - ${size.width / 2}px)`,
	top: centreY === undefined ? `calc(50% - ${size.height / 2}px)` : `${centreY - size.height / 2}px`,
	width: `${size.width}px`,
	height: `${size.height}px`,
	cursor: props.disableHandlers ? undefined : cursor,
});

const trackDistribution = (align: string, free: number, count: number) => {
	if (free <= 0) return { offset: 0, spread: 0 };
	const keyword = align.replace(/^(safe|unsafe)\s+/, "");
	if (keyword === "center") return { offset: free / 2, spread: 0 };
	if (["end", "flex-end", "right"].includes(keyword)) return { offset: free, spread: 0 };
	if (keyword === "space-between") return { offset: 0, spread: free / (count - 1) };
	if (keyword === "space-around") return { offset: free / count / 2, spread: free / count };
	if (keyword === "space-evenly") return { offset: free / (count + 1), spread: free / (count + 1) };
	return { offset: 0, spread: 0 };
};

// A grid's tracks come back in pixels, so its seams are exact even where an item spans rows or
// a cell is empty and the children show nothing.
const trackSeams = (track: Track, from: number, to: number, gap: number, reach: Seam): Seam[] | null => {
	const sizes = track.template.match(/-?[\d.]+px/g)?.map(getNumberFromPx);
	if (!sizes || sizes.length < 2) return null;

	const used = sizes.reduce((sum, size) => sum + size, 0) + gap * (sizes.length - 1);
	const { offset, spread } = trackDistribution(track.align, to - from - used, sizes.length);
	const width = gap + spread;
	let edge = from + offset;
	const seams = sizes.slice(0, -1).map((size) => {
		edge += size + width;
		return { from: edge - width, to: edge };
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

// A column's pill sits level with the middle of the first line, measured from the band's top.
const columnPillY = (rows: Seam[], content: Box) =>
	(((rows[0]?.from ?? content.y1) - content.y0) / 2) * canvasProps.scale;

type Axis = "column" | "row";

// Column seams are vertical bands between side-by-side children, row seams horizontal ones between lines.
const axisBands = {
	column: {
		position: Position.Right,
		thickness: "width",
		cursor: horizontalCursor,
		handleSize: sideHandleSize,
	},
	row: { position: Position.Bottom, thickness: "height", cursor: verticalCursor, handleSize: longHandleSize },
} as const;

const seamBox = (axis: Axis, seam: Seam, content: Box): Box =>
	axis === "column"
		? { x0: seam.from, x1: seam.to, y0: content.y0, y1: content.y1 }
		: { x0: content.x0, x1: content.x1, y0: seam.from, y1: seam.to };

// One band per seam, stretched across the whole content box.
const seamBands = (axis: Axis, seams: Seam[], content: Box, gap: number, pillY?: number): GapBand[] => {
	const { position, thickness, cursor, handleSize } = axisBands[axis];
	const size = handleSize.value;
	return seams.map((seam, index) => {
		const draggable = isDraggable(seam.to - seam.from);
		return {
			key: `${axis}-${index}`,
			position,
			draggable,
			filled: gap > 0,
			style: bandStyle(seamBox(axis, seam, content), thickness, draggable ? cursor.value : undefined),
			handleStyle: handleStyle(size, cursor.value, pillY),
		};
	});
};

const gapBands = computed<GapBand[]>(() => {
	if (!layout.value) return [];
	const { lines, content, gap, tracks, reach } = layout.value;
	const columns =
		trackSeams(tracks.column, content.x0, content.x1, gap.column, reach.column) ?? columnSeams(lines);
	const rows = trackSeams(tracks.row, content.y0, content.y1, gap.row, reach.row) ?? rowSeams(lines);
	return [
		...seamBands("column", columns, content, gap.column, columnPillY(rows, content)),
		...seamBands("row", rows, content, gap.row),
	];
});

const getGapValue = (position: Position) => getSpacingValue("gap", position);

const handleGap = (ev: MouseEvent, band: GapBand) => {
	if (props.disableHandlers) return;
	startSpacingDrag(ev, band.position, {
		property: "gap",
		fallback: 0,
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
