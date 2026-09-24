<template>
	<div class="group" @click.stop>
		<div class="pointer-events-none" :class="fillOpacity">
			<div
				v-for="side in Object.values(Position)"
				v-show="isActive(side)"
				:key="side"
				class="absolute bg-purple-300"
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
			ref="topPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Top)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Top)"
				:class="[isEmpty(Position.Top) ? 'opacity-80' : 'opacity-40', { hidden: updating }]"
				@mouseenter="hoveredSide = Position.Top"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Top)" />
			<div class="m-auto text-sm text-purple-900 opacity-70" v-show="updating">
				{{ getPaddingValue(Position.Top) }}
			</div>
		</div>
		<div
			class="padding-handler absolute bottom-0 flex w-full"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
				cursor: isDraggable(bottomPaddingHandlerHeight) ? verticalCursor : undefined,
			}"
			:class="isDraggable(bottomPaddingHandlerHeight) ? 'pointer-events-auto' : 'pointer-events-none'"
			ref="bottomPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Bottom)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Bottom)"
				:class="[isEmpty(Position.Bottom) ? 'opacity-80' : 'opacity-40', { hidden: updating }]"
				@mouseenter="hoveredSide = Position.Bottom"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Bottom)" />
			<div class="m-auto text-sm text-purple-900 opacity-70" v-show="updating">
				{{ getPaddingValue(Position.Bottom) }}
			</div>
		</div>
		<div
			class="padding-handler absolute left-0 flex h-full"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
				cursor: isDraggable(leftPaddingHandlerWidth) ? horizontalCursor : undefined,
			}"
			:class="isDraggable(leftPaddingHandlerWidth) ? 'pointer-events-auto' : 'pointer-events-none'"
			ref="leftPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Left)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Left)"
				:class="[isEmpty(Position.Left) ? 'opacity-80' : 'opacity-40', { hidden: updating }]"
				@mouseenter="hoveredSide = Position.Left"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Left)" />
			<div class="m-auto text-sm text-purple-900 opacity-70" v-show="updating">
				{{ getPaddingValue(Position.Left) }}
			</div>
		</div>
		<div
			class="padding-handler absolute right-0 flex h-full"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
				cursor: isDraggable(rightPaddingHandlerWidth) ? horizontalCursor : undefined,
			}"
			:class="isDraggable(rightPaddingHandlerWidth) ? 'pointer-events-auto' : 'pointer-events-none'"
			ref="rightPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Right)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 before:absolute before:-inset-2 before:content-[''] hover:scale-125"
				v-show="showHandle"
				:style="pillStyle(Position.Right)"
				:class="[isEmpty(Position.Right) ? 'opacity-80' : 'opacity-40', { hidden: updating }]"
				@mouseenter="hoveredSide = Position.Right"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Right)" />
			<div class="m-auto text-sm text-purple-900 opacity-70" v-show="updating">
				{{ getPaddingValue(Position.Right) }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { useRotatedCursors } from "@/composables/useRotatedCursors";
import {
	EMPTY_SPACING_PILL_GROWTH,
	HANDLE_MIN_SCALE,
	Position,
	useSpacingHandler,
} from "@/composables/useSpacingHandler";
import { useMouseInElement } from "@vueuse/core";
import { Ref, computed, ref, watchEffect } from "vue";
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
	},
);

const emit = defineEmits(["update"]);
const {
	canvasProps,
	updating,
	activeSides,
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

const topPaddingHandler = ref<HTMLElement>();
const bottomPaddingHandler = ref<HTMLElement>();
const leftPaddingHandler = ref<HTMLElement>();
const rightPaddingHandler = ref<HTMLElement>();

// Thin bands let clicks through to the block, so their hover is read off the pointer position.
const pointerOver = (band: Ref<HTMLElement | undefined>) => {
	const { isOutside } = useMouseInElement(band);
	return computed(() => !isOutside.value);
};
const overBand = {
	[Position.Top]: pointerOver(topPaddingHandler),
	[Position.Bottom]: pointerOver(bottomPaddingHandler),
	[Position.Left]: pointerOver(leftPaddingHandler),
	[Position.Right]: pointerOver(rightPaddingHandler),
};

const hoveredSide = ref<Position | null>(null);
const fillOpacity = computed(() => (updating.value ? "opacity-70" : "opacity-40"));
const fillPlacement = {
	[Position.Top]: "left-0 top-0 w-full",
	[Position.Bottom]: "bottom-0 left-0 w-full",
	[Position.Left]: "left-0 top-0 h-full",
	[Position.Right]: "right-0 top-0 h-full",
};
const isActive = (side: Position) =>
	updating.value ? activeSides.value.includes(side) : hoveredSide.value === side || overBand[side].value;

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

const contentShift = computed(() => ({
	x: (leftPaddingHandlerWidth.value - rightPaddingHandlerWidth.value) / 2,
	y: (topPaddingHandlerHeight.value - bottomPaddingHandlerHeight.value) / 2,
}));

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

const pillStyle = (side: Position) => {
	const isLong = side === Position.Top || side === Position.Bottom;
	const size = isLong ? longHandleSize.value : sideHandleSize.value;
	const growth = isEmpty(side) ? EMPTY_SPACING_PILL_GROWTH : 1;
	return handleStyle(
		{ width: size.width * growth, height: size.height * growth },
		isLong ? { x: contentShift.value.x, y: 0 } : { x: 0, y: contentShift.value.y },
		isLong ? verticalCursor.value : horizontalCursor.value,
	);
};

const handlePadding = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	hoveredSide.value = null;
	startSpacingDrag(ev, position, {
		property: "padding",
		fallback: getNumberFromPx(getComputedStyle(props.target).getPropertyValue(`padding-${position}`)),
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
