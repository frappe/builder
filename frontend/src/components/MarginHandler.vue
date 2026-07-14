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
					cursor: disableHandlers ? undefined : verticalCursor,
				}"
				:class="{ hidden: updating }"
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
					cursor: disableHandlers ? undefined : horizontalCursor,
				}"
				:class="{ hidden: updating }"
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
					cursor: disableHandlers ? undefined : horizontalCursor,
				}"
				:class="{ hidden: updating }"
				@mousedown.stop="handleMargin($event, Position.Right)" />
			<div class="m-auto text-sm text-yellow-900" v-show="updating">
				{{ blockStyles.marginRight || "auto" }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { useRotatedCursors } from "@/composables/useRotatedCursors";
import { Position, useSpacingHandler } from "@/composables/useSpacingHandler";
import { startDrag } from "@/utils/cursor";
import { toLocalDelta } from "@/utils/rotation";
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
const { canvasProps, updating, blockStyles, handleBorderWidth, longHandleSize, sideHandleSize } =
	useSpacingHandler(
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
	blockStyles.value.marginTop;
	blockStyles.value.marginBottom;
	blockStyles.value.marginLeft;
	blockStyles.value.marginRight;
	blockStyles.value.margin;
	blockStyles.value.display;
	return getNumberFromPx(getComputedStyle(props.target)[`margin${side}`]) * canvasProps.scale;
};

const topHandle = computed(() => {
	const { width, height } = longHandleSize.value;
	return {
		width,
		height,
		bottom: `clamp(0px, calc(4px * ${canvasProps.scale}), 12px)`,
		left: `calc(50% - ${width / 2}px)`,
	};
});

const bottomHandle = computed(() => {
	const { width, height } = longHandleSize.value;
	return {
		width,
		height,
		bottom: `clamp(-16px, calc(-8px * ${canvasProps.scale}), 2px)`,
		left: `calc(50% - ${width / 2}px)`,
	};
});

const leftHandle = computed(() => {
	const { width, height } = sideHandleSize.value;
	return {
		width,
		height,
		right: `clamp(0px, calc(4px * ${canvasProps.scale}), 12px)`,
		top: `calc(50% - ${height / 2}px)`,
	};
});

const rightHandle = computed(() => {
	const { width, height } = sideHandleSize.value;
	return {
		width,
		height,
		right: `clamp(-16px, calc(-8px * ${canvasProps.scale}), 2px)`,
		top: `calc(50% - ${height / 2}px)`,
	};
});

const handleMargin = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	ev.preventDefault();
	updating.value = true;
	const startY = ev.clientY;
	const startX = ev.clientX;
	const target = ev.target as HTMLElement;

	const startTop = getNumberFromPx(blockStyles.value.marginTop) || 0;
	const startBottom = getNumberFromPx(blockStyles.value.marginBottom) || 0;
	const startLeft = getNumberFromPx(blockStyles.value.marginLeft) || 0;
	const startRight = getNumberFromPx(blockStyles.value.marginRight) || 0;

	startDrag({
		cursor: window.getComputedStyle(target).cursor,
		onMove: (mouseMoveEvent) => {
			let movement = 0;
			let affectingAxis = null;
			props.onUpdate && props.onUpdate();
			const dx = mouseMoveEvent.clientX - startX;
			const dy = mouseMoveEvent.clientY - startY;
			const { x: localX, y: localY } = toLocalDelta(dx, dy, rotation.value);
			if (position === Position.Top) {
				// top/left handles sit outside the block, so dragging away from it (up/left) grows the margin
				movement = Math.round(Math.max(startTop - localY, 0));
				props.targetBlock.setStyle("marginTop", movement + "px");
				affectingAxis = "y";
			} else if (position === Position.Bottom) {
				movement = Math.round(Math.max(startBottom + localY, 0));
				props.targetBlock.setStyle("marginBottom", movement + "px");
				affectingAxis = "y";
			} else if (position === Position.Left) {
				movement = Math.round(Math.max(startLeft - localX, 0));
				props.targetBlock.setStyle("marginLeft", movement + "px");
				affectingAxis = "x";
			} else if (position === Position.Right) {
				movement = Math.round(Math.max(startRight + localX, 0));
				props.targetBlock.setStyle("marginRight", movement + "px");
				affectingAxis = "x";
			}

			if (mouseMoveEvent.shiftKey) {
				props.targetBlock.setStyle("marginTop", movement + "px");
				props.targetBlock.setStyle("marginBottom", movement + "px");
				props.targetBlock.setStyle("marginLeft", movement + "px");
				props.targetBlock.setStyle("marginRight", movement + "px");
			} else if (mouseMoveEvent.altKey) {
				if (affectingAxis === "y") {
					props.targetBlock.setStyle("marginTop", movement + "px");
					props.targetBlock.setStyle("marginBottom", movement + "px");
				} else if (affectingAxis === "x") {
					props.targetBlock.setStyle("marginLeft", movement + "px");
					props.targetBlock.setStyle("marginRight", movement + "px");
				}
			}
		},
		onEnd: () => {
			updating.value = false;
		},
	});
};
</script>
