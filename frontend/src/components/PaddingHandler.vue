<template>
	<div class="group" @click.stop>
		<CursorTooltip v-if="updating" tone="blue" :position="cursorPosition">
			{{ getPaddingValue(activeSides[0]) }}
		</CursorTooltip>
		<!-- clipped to stay inside the 2px selection ring, which is drawn under the bands -->
		<div class="pointer-events-none absolute inset-0 opacity-30 [clip-path:inset(2px)]">
			<div
				v-for="side in Object.values(Position)"
				v-show="isActive(side)"
				:key="side"
				class="absolute bg-blue-400"
				:class="fillPlacement[side]"
				:style="fillSize(side)" />
		</div>
		<div
			class="padding-handler absolute flex w-full"
			:style="{
				height: topPaddingHandlerHeight + 'px',
				cursor: isDraggable(topPaddingHandlerHeight) ? verticalCursor : undefined,
			}"
			:class="isDraggable(topPaddingHandlerHeight) ? 'pointer-events-auto' : 'pointer-events-none'"
			@mousedown.stop="handlePadding($event, Position.Top)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-blue-400 bg-blue-300 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Top)"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Top)" />
		</div>
		<div
			class="padding-handler absolute bottom-0 flex w-full"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
				cursor: isDraggable(bottomPaddingHandlerHeight) ? verticalCursor : undefined,
			}"
			:class="isDraggable(bottomPaddingHandlerHeight) ? 'pointer-events-auto' : 'pointer-events-none'"
			@mousedown.stop="handlePadding($event, Position.Bottom)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-blue-400 bg-blue-300 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Bottom)"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Bottom)" />
		</div>
		<div
			class="padding-handler absolute left-0 flex h-full"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
				cursor: isDraggable(leftPaddingHandlerWidth) ? horizontalCursor : undefined,
			}"
			:class="isDraggable(leftPaddingHandlerWidth) ? 'pointer-events-auto' : 'pointer-events-none'"
			@mousedown.stop="handlePadding($event, Position.Left)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-blue-400 bg-blue-300 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Left)"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Left)" />
		</div>
		<div
			class="padding-handler absolute right-0 flex h-full"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
				cursor: isDraggable(rightPaddingHandlerWidth) ? horizontalCursor : undefined,
			}"
			:class="isDraggable(rightPaddingHandlerWidth) ? 'pointer-events-auto' : 'pointer-events-none'"
			@mousedown.stop="handlePadding($event, Position.Right)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-blue-400 bg-blue-300 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Right)"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Right)" />
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { useRotatedCursors } from "@/composables/useRotatedCursors";
import { HANDLE_MIN_SCALE, Position, useSpacingHandler } from "@/composables/useSpacingHandler";
import { computed, watchEffect } from "vue";
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

const fillPlacement = {
	[Position.Top]: "left-0 top-0 w-full",
	[Position.Bottom]: "bottom-0 left-0 w-full",
	[Position.Left]: "left-0 top-0 h-full",
	[Position.Right]: "right-0 top-0 h-full",
};
const isActive = (side: Position) => updating.value && activeSides.value.includes(side);

const { rotation, horizontalCursor, verticalCursor } = useRotatedCursors(
	() => props.target as Element,
	() => props.targetBlock,
);

const MIN_DRAGGABLE_BAND = 8;

const showHandle = computed(() => canvasProps.scale > HANDLE_MIN_SCALE);
const isDraggable = (thickness: number) => !props.disableHandlers && thickness >= MIN_DRAGGABLE_BAND;

const topPaddingHandlerHeight = computed(() => {
	return getPadding("Top");
});

const bottomPaddingHandlerHeight = computed(() => {
	return getPadding("Bottom");
});

const leftPaddingHandlerWidth = computed(() => {
	return getPadding("Left");
});

const rightPaddingHandlerWidth = computed(() => {
	return getPadding("Right");
});

const getPadding = (side: "Top" | "Left" | "Right" | "Bottom") => {
	blockStyles.value.padding;
	return getNumberFromPx(getComputedStyle(props.target)[`padding${side}`]) * canvasProps.scale;
};

const getPaddingValue = (position: Position) => getSpacingValue("padding", position);

// The pill sits in the middle of its band on both axes
const handleStyle = (
	size: { width: number; height: number },
	offset: { x: number; y: number },
	cursor: string,
) => ({
	borderWidth: handleBorderWidth.value,
	left: `calc(50% + ${offset.x - size.width / 2}px)`,
	top: `calc(50% + ${offset.y - size.height / 2}px)`,
	width: `${size.width}px`,
	height: `${size.height}px`,
	cursor: props.disableHandlers ? undefined : cursor,
});
const bandThickness = {
	[Position.Top]: topPaddingHandlerHeight,
	[Position.Bottom]: bottomPaddingHandlerHeight,
	[Position.Left]: leftPaddingHandlerWidth,
	[Position.Right]: rightPaddingHandlerWidth,
};
const fillSize = (side: Position) => {
	const isLong = side === Position.Top || side === Position.Bottom;
	return { [isLong ? "height" : "width"]: `${bandThickness[side].value}px` };
};
const isEmpty = (side: Position) => bandThickness[side].value === 0;

// The selection ring (ring-2 ring-inset in BlockEditor) is drawn inside the edge, so a
// pill on an empty band is nudged inward by half its width to sit centred on the line.
const RING_CENTRE_INSET = 1;
const inwardDirection = {
	[Position.Top]: 1,
	[Position.Bottom]: -1,
	[Position.Left]: 1,
	[Position.Right]: -1,
};

const pillStyle = (side: Position) => {
	const isLong = side === Position.Top || side === Position.Bottom;
	const size = isLong ? longHandleSize.value : sideHandleSize.value;
	const inset = isEmpty(side) ? RING_CENTRE_INSET * inwardDirection[side] : 0;
	return handleStyle(
		size,
		isLong ? { x: 0, y: inset } : { x: inset, y: 0 },
		isLong ? verticalCursor.value : horizontalCursor.value,
	);
};

const handlePadding = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	startSpacingDrag(ev, position, {
		property: "padding",
		fallback: getNumberFromPx(getComputedStyle(props.target).getPropertyValue(`padding-${position}`)),
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
