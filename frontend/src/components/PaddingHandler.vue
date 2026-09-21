<template>
	<div
		class="group"
		:class="{
			'opacity-40': !updating,
			'opacity-70': updating,
		}"
		@click.stop>
		<div
			class="padding-handler pointer-events-none absolute z-10 flex w-full"
			:style="{
				height: topPaddingHandlerHeight + 'px',
			}"
			:class="{ 'bg-purple-300': isActive(Position.Top) }"
			ref="topPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(topPaddingHandlerHeight)"
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
			class="padding-handler pointer-events-none absolute bottom-0 z-10 flex w-full"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
			}"
			:class="{ 'bg-purple-300': isActive(Position.Bottom) }"
			ref="bottomPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(bottomPaddingHandlerHeight)"
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
			class="padding-handler pointer-events-none absolute left-0 z-10 flex h-full"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
			}"
			:class="{ 'bg-purple-300': isActive(Position.Left) }"
			ref="leftPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(leftPaddingHandlerWidth)"
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
			class="padding-handler pointer-events-none absolute right-0 z-10 flex h-full"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
			}"
			:class="{ 'bg-purple-300': isActive(Position.Right) }"
			ref="rightPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(rightPaddingHandlerWidth)"
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
		showBands?: boolean;
		onUpdate?: () => void;
		breakpoint?: string;
		target: HTMLElement | SVGElement;
	}>(),
	{
		disableHandlers: false,
		showBands: false,
		breakpoint: "desktop",
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

// A drag can carry the pointer out of the block, so the handles stay while it runs.
const bandsVisible = computed(() => props.showBands || updating.value);

const topPaddingHandler = ref<HTMLElement>();
const bottomPaddingHandler = ref<HTMLElement>();
const leftPaddingHandler = ref<HTMLElement>();
const rightPaddingHandler = ref<HTMLElement>();

// The bands let clicks through to the block, so their hover is read off the pointer position.
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

// A band is filled only while it or its pill is hovered, or it is being dragged.
const hoveredSide = ref<Position | null>(null);
const draggedSide = ref<Position | null>(null);
const isActive = (side: Position) =>
	updating.value ? draggedSide.value === side : hoveredSide.value === side || overBand[side].value;

const { rotation, horizontalCursor, verticalCursor } = useRotatedCursors(
	() => props.target as Element,
	() => props.targetBlock,
);

const HANDLE_MIN_SCALE = 0.5;

const showHandle = (band: number) => bandsVisible.value && canvasProps.scale > HANDLE_MIN_SCALE && band > 0;

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
	draggedSide.value = position;
	hoveredSide.value = null;
	startSpacingDrag(ev, position, {
		property: "padding",
		fallback: 5,
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
