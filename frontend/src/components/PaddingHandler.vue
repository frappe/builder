<template>
	<div
		class="group"
		:class="{
			'opacity-40': !updating,
			'opacity-70': updating,
		}"
		@click.stop>
		<div
			class="padding-handler absolute z-10 flex w-full"
			:style="{
				height: topPaddingHandlerHeight + 'px',
				cursor: isDraggable(topPaddingHandlerHeight) ? verticalCursor : undefined,
			}"
			:class="[
				isDraggable(topPaddingHandlerHeight) ? 'pointer-events-auto' : 'pointer-events-none',
				{ 'bg-purple-300': isActive(Position.Top) },
			]"
			ref="topPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Top)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle"
				:style="longHandle"
				:class="{ hidden: updating }"
				@mouseenter="hoveredSide = Position.Top"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Top)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ getPaddingValue(Position.Top) }}
			</div>
		</div>
		<div
			class="padding-handler absolute bottom-0 z-10 flex w-full"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
				cursor: isDraggable(bottomPaddingHandlerHeight) ? verticalCursor : undefined,
			}"
			:class="[
				isDraggable(bottomPaddingHandlerHeight) ? 'pointer-events-auto' : 'pointer-events-none',
				{ 'bg-purple-300': isActive(Position.Bottom) },
			]"
			ref="bottomPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Bottom)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle"
				:style="longHandle"
				:class="{ hidden: updating }"
				@mouseenter="hoveredSide = Position.Bottom"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Bottom)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ getPaddingValue(Position.Bottom) }}
			</div>
		</div>
		<div
			class="padding-handler absolute left-0 z-10 flex h-full"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
				cursor: isDraggable(leftPaddingHandlerWidth) ? horizontalCursor : undefined,
			}"
			:class="[
				isDraggable(leftPaddingHandlerWidth) ? 'pointer-events-auto' : 'pointer-events-none',
				{ 'bg-purple-300': isActive(Position.Left) },
			]"
			ref="leftPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Left)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle"
				:style="sideHandle"
				:class="{ hidden: updating }"
				@mouseenter="hoveredSide = Position.Left"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Left)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ getPaddingValue(Position.Left) }}
			</div>
		</div>
		<div
			class="padding-handler absolute right-0 z-10 flex h-full"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
				cursor: isDraggable(rightPaddingHandlerWidth) ? horizontalCursor : undefined,
			}"
			:class="[
				isDraggable(rightPaddingHandlerWidth) ? 'pointer-events-auto' : 'pointer-events-none',
				{ 'bg-purple-300': isActive(Position.Right) },
			]"
			ref="rightPaddingHandler"
			@mousedown.stop="handlePadding($event, Position.Right)">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle"
				:style="sideHandle"
				:class="{ hidden: updating }"
				@mouseenter="hoveredSide = Position.Right"
				@mouseleave="hoveredSide = null"
				@mousedown.stop="handlePadding($event, Position.Right)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ getPaddingValue(Position.Right) }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { useRotatedCursors } from "@/composables/useRotatedCursors";
import { Position, useSpacingHandler } from "@/composables/useSpacingHandler";
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
const isActive = (side: Position) =>
	updating.value ? activeSides.value.includes(side) : hoveredSide.value === side || overBand[side].value;

const { rotation, horizontalCursor, verticalCursor } = useRotatedCursors(
	() => props.target as Element,
	() => props.targetBlock,
);

const HANDLE_MIN_SCALE = 0.5;

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
const longHandle = computed(() =>
	handleStyle(longHandleSize.value, { x: contentShift.value.x, y: 0 }, verticalCursor.value),
);

const sideHandle = computed(() =>
	handleStyle(sideHandleSize.value, { x: 0, y: contentShift.value.y }, horizontalCursor.value),
);

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
