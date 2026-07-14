<template>
	<div
		class="group"
		:class="{
			'opacity-40': !updating,
			'opacity-70': updating,
		}"
		@click.stop>
		<div
			class="padding-handler pointer-events-none absolute flex w-full bg-purple-400"
			:style="{
				height: topPaddingHandlerHeight + 'px',
			}"
			ref="topPaddingHandler">
			<div
				class="pointer-events-auto absolute left-[50%] rounded-full border-2 border-purple-500 bg-purple-400 hover:scale-125"
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
				@mousedown.stop="handlePadding($event, Position.Top)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingTop }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute bottom-0 flex w-full bg-purple-400"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
			}"
			ref="bottomPaddingHandler">
			<div
				class="pointer-events-auto absolute left-[50%] rounded-full border-2 border-purple-500 bg-purple-400 hover:scale-125"
				v-show="canvasProps.scale > 0.5"
				:style="{
					borderWidth: handleBorderWidth,
					top: bottomHandle.top,
					left: bottomHandle.left,
					height: bottomHandle.height + 'px',
					width: bottomHandle.width + 'px',
					cursor: disableHandlers ? undefined : verticalCursor,
				}"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Bottom)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingBottom }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute left-0 flex h-full bg-purple-400"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
			}"
			ref="leftPaddingHandler">
			<div
				class="pointer-events-auto absolute top-[50%] rounded-full border-2 border-purple-500 bg-purple-400 hover:scale-125"
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
				@mousedown.stop="handlePadding($event, Position.Left)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingLeft }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute right-0 flex h-full bg-purple-400"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
			}"
			ref="rightPaddingHandler">
			<div
				class="pointer-events-auto absolute top-[50%] rounded-full border-2 border-purple-500 bg-purple-400 hover:scale-125"
				v-show="canvasProps.scale > 0.5"
				:style="{
					borderWidth: handleBorderWidth,
					left: rightHandle.left,
					top: rightHandle.top,
					height: rightHandle.height + 'px',
					width: rightHandle.width + 'px',
					cursor: disableHandlers ? undefined : horizontalCursor,
				}"
				:class="{ hidden: updating }"
				@mousedown.stop="handlePadding($event, Position.Right)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingRight }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import resizeCursorSvg from "@/assets/resize-cursor.svg?raw";
import { Position, useSpacingHandler } from "@/composables/useSpacingHandler";
import { clearDragCursor, getRotatedCursor, setDragCursor } from "@/utils/cursor";
import { getTotalRotation, toLocalDelta } from "@/utils/rotation";
import { computed, ref, watchEffect } from "vue";
import { getNumberFromPx } from "../utils/helpers";

import { toast } from "frappe-ui";

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
const { canvasProps, updating, blockStyles, handleBorderWidth, longHandleSize, sideHandleSize } =
	useSpacingHandler(
		() => props.targetBlock,
		() => props.breakpoint,
	);

watchEffect(() => {
	emit("update", updating.value);
});

// the block's rendered angle, so the cursor and drag axes stay correct when rotated
const rotation = computed(() => getTotalRotation(props.target as Element, props.targetBlock));
const horizontalCursor = computed(() => getRotatedCursor(resizeCursorSvg, rotation.value, "ew-resize"));
const verticalCursor = computed(() => getRotatedCursor(resizeCursorSvg, rotation.value + 90, "ns-resize"));

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
	blockStyles.value.paddingRight;
	blockStyles.value.paddingTop;
	blockStyles.value.paddingBottom;
	blockStyles.value.paddingLeft;
	blockStyles.value.padding;
	return getNumberFromPx(getComputedStyle(props.target)[`padding${side}`]) * canvasProps.scale;
};

const topHandle = computed(() => {
	const { width, height } = longHandleSize.value;
	return {
		width,
		height,
		bottom: `clamp(-20px, calc(-10px * ${canvasProps.scale}), -6px)`,
		left: `calc(50% - ${width / 2}px)`,
	};
});

const bottomHandle = computed(() => {
	const { width, height } = longHandleSize.value;
	return {
		width,
		height,
		top: `clamp(-20px, calc(-10px * ${canvasProps.scale}), -6px)`,
		left: `calc(50% - ${width / 2}px)`,
	};
});

const leftHandle = computed(() => {
	const { width, height } = sideHandleSize.value;
	return {
		width,
		height,
		right: `clamp(-20px, calc(-10px * ${canvasProps.scale}), -6px)`,
		top: `calc(50% - ${height / 2}px)`,
	};
});

const rightHandle = computed(() => {
	const { width, height } = sideHandleSize.value;
	return {
		width,
		height,
		left: `clamp(-20px, calc(-10px * ${canvasProps.scale}), -6px)`,
		top: `calc(50% - ${height / 2}px)`,
	};
});

const messageShown = ref(false);

const handlePadding = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	// if (!messageShown.value && !(ev.shiftKey || ev.altKey)) {
	// 	showToast();
	// 	messageShown.value = true;
	// }
	updating.value = true;
	const startY = ev.clientY;
	const startX = ev.clientX;
	const target = ev.target as HTMLElement;

	const startTop = getNumberFromPx(blockStyles.value.paddingTop) || 5;
	const startBottom = getNumberFromPx(blockStyles.value.paddingBottom) || 5;
	const startLeft = getNumberFromPx(blockStyles.value.paddingLeft) || 5;
	const startRight = getNumberFromPx(blockStyles.value.paddingRight) || 5;

	setDragCursor(window.getComputedStyle(target).cursor);

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		let movement = 0;
		let affectingAxis = null;
		props.onUpdate && props.onUpdate();
		const dx = mouseMoveEvent.clientX - startX;
		const dy = mouseMoveEvent.clientY - startY;
		const { x: localX, y: localY } = toLocalDelta(dx, dy, rotation.value);
		if (position === Position.Top) {
			movement = Math.round(Math.max(startTop + localY, 0));
			props.targetBlock.setStyle("paddingTop", movement + "px");
			affectingAxis = "y";
		} else if (position === Position.Bottom) {
			movement = Math.round(Math.max(startBottom - localY, 0));
			props.targetBlock.setStyle("paddingBottom", movement + "px");
			affectingAxis = "y";
		} else if (position === Position.Left) {
			movement = Math.round(Math.max(startLeft + localX, 0));
			props.targetBlock.setStyle("paddingLeft", movement + "px");
			affectingAxis = "x";
		} else if (position === Position.Right) {
			movement = Math.round(Math.max(startRight - localX, 0));
			props.targetBlock.setStyle("paddingRight", movement + "px");
			affectingAxis = "x";
		}

		if (mouseMoveEvent.altKey) {
			if (affectingAxis === "y") {
				props.targetBlock.setStyle("paddingTop", movement + "px");
				props.targetBlock.setStyle("paddingBottom", movement + "px");
			} else if (affectingAxis === "x") {
				props.targetBlock.setStyle("paddingLeft", movement + "px");
				props.targetBlock.setStyle("paddingRight", movement + "px");
			}
		} else if (mouseMoveEvent.shiftKey) {
			props.targetBlock.setStyle("paddingTop", movement + "px");
			props.targetBlock.setStyle("paddingBottom", movement + "px");
			props.targetBlock.setStyle("paddingLeft", movement + "px");
			props.targetBlock.setStyle("paddingRight", movement + "px");
		}

		mouseMoveEvent.preventDefault();
		mouseMoveEvent.stopPropagation();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			clearDragCursor();
			document.removeEventListener("mousemove", mousemove);
			updating.value = false;
			mouseUpEvent.preventDefault();
		},
		{ once: true },
	);
};

let showToast = () =>
	toast('Press "shift" key to apply padding to all sides and "alt" key to apply padding on either sides.');
</script>
