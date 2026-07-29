<template>
	<div
		class="group"
		:class="{
			'opacity-40': !updating,
			'opacity-70': updating,
		}"
		@click.stop>
		<div
			class="margin-handler pointer-events-none absolute flex w-full bg-yellow-200"
			:style="{
				height: topMarginHandlerHeight + 'px',
				top: `calc(0% - ${topMarginHandlerHeight}px)`,
			}"
			ref="topMarginHandler">
			<div
				class="pointer-events-auto absolute left-[50%] rounded-full border-2 border-yellow-800 bg-yellow-400 hover:scale-125"
				v-show="canvasProps.scale > 0.5"
				:style="{
					borderWidth: handleBorderWidth,
					bottom: topHandle.bottom,
					left: topHandle.left,
					height: topHandle.height + 'px',
					width: topHandle.width + 'px',
					cursor: disableHandlers ? undefined : verticalCursor,
				}"
				:class="{ hidden: updating }"
				@mousedown.stop="handleMargin($event, Position.Top)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ getMarginValue(Position.Top) || "auto" }}
			</div>
		</div>
		<div
			class="margin-handler pointer-events-none absolute bottom-0 flex w-full bg-yellow-200"
			:style="{
				height: bottomMarginHandlerHeight + 'px',
				bottom: `calc(0% - ${bottomMarginHandlerHeight}px)`,
			}"
			ref="bottomMarginHandler">
			<div
				class="pointer-events-auto absolute left-[50%] rounded-full border-2 border-yellow-800 bg-yellow-400 hover:scale-125"
				v-show="canvasProps.scale > 0.5"
				:style="{
					borderWidth: handleBorderWidth,
					bottom: bottomHandle.bottom,
					left: bottomHandle.left,
					height: bottomHandle.height + 'px',
					width: bottomHandle.width + 'px',
					cursor: disableHandlers ? undefined : verticalCursor,
				}"
				:class="{ hidden: updating }"
				@mousedown.stop="handleMargin($event, Position.Bottom)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ getMarginValue(Position.Bottom) || "auto" }}
			</div>
		</div>
		<div
			class="margin-handler pointer-events-none absolute left-0 flex h-full bg-yellow-200"
			:style="{
				width: leftMarginHandlerWidth + 'px',
				left: `calc(0% - ${leftMarginHandlerWidth}px)`,
			}"
			ref="leftMarginHandler">
			<div
				class="pointer-events-auto absolute top-[50%] rounded-full border-2 border-yellow-800 bg-yellow-400 hover:scale-125"
				v-show="canvasProps.scale > 0.5"
				:style="{
					borderWidth: handleBorderWidth,
					right: leftHandle.right,
					top: leftHandle.top,
					height: leftHandle.height + 'px',
					width: leftHandle.width + 'px',
					cursor: disableHandlers ? undefined : horizontalCursor,
				}"
				:class="{ hidden: updating }"
				@mousedown.stop="handleMargin($event, Position.Left)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ getMarginValue(Position.Left) || "auto" }}
			</div>
		</div>
		<div
			class="margin-handler pointer-events-none absolute right-0 flex h-full bg-yellow-200"
			:style="{
				width: rightMarginHandlerWidth + 'px',
				right: `calc(0% - ${rightMarginHandlerWidth}px)`,
			}"
			ref="rightMarginHandler">
			<div
				class="pointer-events-auto absolute top-[50%] rounded-full border-2 border-yellow-800 bg-yellow-400 hover:scale-125"
				v-show="canvasProps.scale > 0.5"
				:style="{
					borderWidth: handleBorderWidth,
					right: rightHandle.right,
					top: rightHandle.top,
					height: rightHandle.height + 'px',
					width: rightHandle.width + 'px',
					cursor: disableHandlers ? undefined : horizontalCursor,
				}"
				:class="{ hidden: updating }"
				@mousedown.stop="handleMargin($event, Position.Right)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ getMarginValue(Position.Right) || "auto" }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { useRotatedCursors } from "@/composables/useRotatedCursors";
import { Position, useSpacingHandler } from "@/composables/useSpacingHandler";
import { getComputedStyleFor } from "@/utils/canvasFrameDom";
import { computed, watchEffect } from "vue";
import { getNumberFromPx } from "../utils/helpers";
const props = withDefaults(
	defineProps<{
		targetBlock: Block;
		target: HTMLElement | SVGElement;
		disableHandlers?: boolean;
		onUpdate?: () => void;
		breakpoint?: string;
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
	canvasPixelsForScreenScale,
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

const topMarginHandlerHeight = computed(() => getMargin("Top"));
const bottomMarginHandlerHeight = computed(() => getMargin("Bottom"));
const leftMarginHandlerWidth = computed(() => getMargin("Left"));
const rightMarginHandlerWidth = computed(() => getMargin("Right"));

const getMargin = (side: "Top" | "Left" | "Right" | "Bottom") => {
	blockStyles.value.margin;
	blockStyles.value.display;
	return getNumberFromPx(getComputedStyleFor(props.target)[`margin${side}`]);
};

const getMarginValue = (position: Position) => getSpacingValue("margin", position);

const topHandle = computed(() => {
	const { width, height } = longHandleSize.value;
	return {
		width,
		height,
		bottom: `${canvasPixelsForScreenScale(4, 0, 12)}px`,
		left: `calc(50% - ${width / 2}px)`,
	};
});

const bottomHandle = computed(() => {
	const { width, height } = longHandleSize.value;
	return {
		width,
		height,
		bottom: `${canvasPixelsForScreenScale(-8, -16, 2)}px`,
		left: `calc(50% - ${width / 2}px)`,
	};
});

const leftHandle = computed(() => {
	const { width, height } = sideHandleSize.value;
	return {
		width,
		height,
		right: `${canvasPixelsForScreenScale(4, 0, 12)}px`,
		top: `calc(50% - ${height / 2}px)`,
	};
});

const rightHandle = computed(() => {
	const { width, height } = sideHandleSize.value;
	return {
		width,
		height,
		right: `${canvasPixelsForScreenScale(-8, -16, 2)}px`,
		top: `calc(50% - ${height / 2}px)`,
	};
});

const handleMargin = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	startSpacingDrag(ev, position, {
		property: "margin",
		fallback: 0,
		getRotation: () => rotation.value,
		onUpdate: props.onUpdate,
	});
};
</script>
