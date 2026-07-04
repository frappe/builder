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
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handleMargin($event, Position.Top)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ blockStyles.marginTop || "auto" }}
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
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handleMargin($event, Position.Bottom)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ blockStyles.marginBottom || "auto" }}
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
				}"
				:class="{
					'cursor-ew-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handleMargin($event, Position.Left)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ blockStyles.marginLeft || "auto" }}
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
				}"
				:class="{
					'cursor-ew-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handleMargin($event, Position.Right)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ blockStyles.marginRight || "auto" }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { Position, useSpacingHandler } from "@/composables/useSpacingHandler";
import { getComputedStyleFor, startCanvasDrag } from "@/utils/canvasFrameDom";
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
	handleBorderWidth,
	longHandleSize,
	sideHandleSize,
	canvasPixelsForScreenScale,
} = useSpacingHandler(
	() => props.targetBlock,
	() => props.breakpoint,
);

watchEffect(() => {
	emit("update", updating.value);
});

const topMarginHandlerHeight = computed(() => {
	blockStyles.value.marginTop;
	blockStyles.value.display;
	blockStyles.value.margin;
	let marginTop = getComputedStyleFor(props.target).marginTop;
	let value = getNumberFromPx(marginTop);
	return value;
});
const bottomMarginHandlerHeight = computed(() => {
	blockStyles.value.marginBottom;
	blockStyles.value.display;
	blockStyles.value.margin;
	let marginBottom = getComputedStyleFor(props.target).marginBottom;
	let value = getNumberFromPx(marginBottom);
	return value;
});
const leftMarginHandlerWidth = computed(() => {
	blockStyles.value.marginLeft;
	blockStyles.value.display;
	blockStyles.value.margin;
	let marginLeft = getComputedStyleFor(props.target).marginLeft;
	let value = getNumberFromPx(marginLeft);
	return value;
});
const rightMarginHandlerWidth = computed(() => {
	blockStyles.value.marginRight;
	blockStyles.value.display;
	blockStyles.value.margin;
	let marginRight = getComputedStyleFor(props.target).marginRight;
	let value = getNumberFromPx(marginRight);
	return value;
});

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
	ev.preventDefault();
	updating.value = true;
	const target = ev.target as HTMLElement;

	const startTop = getNumberFromPx(String(blockStyles.value.marginTop || "")) || 0;
	const startBottom = getNumberFromPx(String(blockStyles.value.marginBottom || "")) || 0;
	const startLeft = getNumberFromPx(String(blockStyles.value.marginLeft || "")) || 0;
	const startRight = getNumberFromPx(String(blockStyles.value.marginRight || "")) || 0;

	startCanvasDrag(ev, props.target, {
		cursor: getComputedStyleFor(target).cursor,
		onMove: ({ event, point, startPoint }) => {
			let movement = 0;
			let affectingAxis = null;
			props.onUpdate?.();
			if (position === Position.Top) {
				movement = Math.max(startTop + point.y - startPoint.y, 0);
				props.targetBlock.setStyle("marginTop", movement + "px");
				affectingAxis = "y";
			} else if (position === Position.Bottom) {
				movement = Math.max(startBottom + point.y - startPoint.y, 0);
				props.targetBlock.setStyle("marginBottom", movement + "px");
				affectingAxis = "y";
			} else if (position === Position.Left) {
				movement = Math.max(startLeft + point.x - startPoint.x, 0);
				props.targetBlock.setStyle("marginLeft", movement + "px");
				affectingAxis = "x";
			} else if (position === Position.Right) {
				movement = Math.max(startRight + point.x - startPoint.x, 0);
				props.targetBlock.setStyle("marginRight", movement + "px");
				affectingAxis = "x";
			}

			if (event.shiftKey) {
				props.targetBlock.setStyle("marginTop", movement + "px");
				props.targetBlock.setStyle("marginBottom", movement + "px");
				props.targetBlock.setStyle("marginLeft", movement + "px");
				props.targetBlock.setStyle("marginRight", movement + "px");
			} else if (event.altKey) {
				if (affectingAxis === "y") {
					props.targetBlock.setStyle("marginTop", movement + "px");
					props.targetBlock.setStyle("marginBottom", movement + "px");
				} else if (affectingAxis === "x") {
					props.targetBlock.setStyle("marginLeft", movement + "px");
					props.targetBlock.setStyle("marginRight", movement + "px");
				}
			}

			event.preventDefault();
		},
		onEnd: (event) => {
			updating.value = false;
			event.preventDefault();
		},
	});
};
</script>
