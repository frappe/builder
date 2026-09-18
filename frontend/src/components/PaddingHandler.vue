<template>
	<div
		class="group"
		:class="{
			'opacity-40': !updating,
			'opacity-70': updating,
		}"
		@click.stop>
		<div
			class="padding-handler pointer-events-none absolute z-10 flex w-full bg-purple-400"
			:style="{
				height: topPaddingHandlerHeight + 'px',
			}"
			ref="topPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(topPaddingHandlerHeight)"
				:style="longHandle"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Top)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ getPaddingValue(Position.Top) }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute bottom-0 z-10 flex w-full bg-purple-400"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
			}"
			ref="bottomPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(bottomPaddingHandlerHeight)"
				:style="longHandle"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Bottom)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ getPaddingValue(Position.Bottom) }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute left-0 z-10 flex h-full bg-purple-400"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
			}"
			ref="leftPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(leftPaddingHandlerWidth)"
				:style="sideHandle"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Left)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ getPaddingValue(Position.Left) }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute right-0 z-10 flex h-full bg-purple-400"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
			}"
			ref="rightPaddingHandler">
			<div
				class="pointer-events-auto absolute z-20 rounded-full border-2 border-purple-900 bg-purple-400 hover:scale-125"
				v-show="showHandle(rightPaddingHandlerWidth)"
				:style="sideHandle"
				:class="{ hidden: updating }"
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
import { computed, watchEffect } from "vue";
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

const HANDLE_MIN_SCALE = 0.5;

const showHandle = (band: number) => canvasProps.scale > HANDLE_MIN_SCALE && band > 0;

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
	startSpacingDrag(ev, position, {
		property: "padding",
		fallback: 5,
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
