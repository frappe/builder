<template>
	<div
		class="group"
		:class="{
			'opacity-40': !updating,
			'opacity-70': updating,
		}"
		@click.stop>
		<div
			class="padding-handler pointer-events-none absolute flex w-full"
			:style="{
				height: topPaddingHandlerHeight + 'px',
			}"
			:class="{
				'bg-transparent': !targetBlock.isSelected(),
				'bg-purple-400': targetBlock.isSelected(),
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
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handlePadding($event, Position.Top)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingTop }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute bottom-0 flex w-full"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
			}"
			:class="{
				'bg-transparent': !targetBlock.isSelected(),
				'bg-purple-400': targetBlock.isSelected(),
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
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handlePadding($event, Position.Bottom)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingBottom }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute left-0 flex h-full"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
			}"
			:class="{
				'bg-transparent': !targetBlock.isSelected(),
				'bg-purple-400': targetBlock.isSelected(),
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
				}"
				:class="{
					'cursor-ew-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handlePadding($event, Position.Left)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingLeft }}
			</div>
		</div>
		<div
			class="padding-handler pointer-events-none absolute right-0 flex h-full"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
			}"
			:class="{
				'bg-transparent': !targetBlock.isSelected(),
				'bg-purple-400': targetBlock.isSelected(),
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
				}"
				:class="{
					'cursor-ew-resize': !disableHandlers,
					hidden: updating,
				}"
				@mousedown.stop="handlePadding($event, Position.Right)" />
			<div class="m-auto text-sm text-purple-900" v-show="updating">
				{{ blockStyles.paddingRight }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { clamp } from "@vueuse/core";
import { computed, inject, ref, watchEffect } from "vue";
import Block from "../utils/block";
import { getNumberFromPx } from "../utils/helpers";

import { toast } from "frappe-ui";
const canvasProps = inject("canvasProps") as CanvasProps;

const props = defineProps({
	targetBlock: {
		type: Block,
		required: true,
	},
	disableHandlers: {
		type: Boolean,
		default: false,
	},
	onUpdate: {
		type: Function,
		default: null,
	},
	breakpoint: {
		type: String,
		default: "desktop",
	},
});

const targetBlock = props.targetBlock;

const updating = ref(false);
const emit = defineEmits(["update"]);

watchEffect(() => {
	emit("update", updating.value);
});

const blockStyles = computed(() => {
	let styleObj = props.targetBlock.baseStyles;
	if (props.breakpoint === "mobile") {
		styleObj = { ...styleObj, ...props.targetBlock.mobileStyles };
	} else if (props.breakpoint === "tablet") {
		styleObj = { ...styleObj, ...props.targetBlock.tabletStyles };
	}
	return styleObj;
});

const topPaddingHandlerHeight = computed(() => {
	return getNumberFromPx(blockStyles.value.paddingTop) * canvasProps.scale;
});
const bottomPaddingHandlerHeight = computed(() => {
	return getNumberFromPx(blockStyles.value.paddingBottom) * canvasProps.scale;
});
const leftPaddingHandlerWidth = computed(() => {
	return getNumberFromPx(blockStyles.value.paddingLeft) * canvasProps.scale;
});
const rightPaddingHandlerWidth = computed(() => {
	return getNumberFromPx(blockStyles.value.paddingRight) * canvasProps.scale;
});

const handleBorderWidth = computed(() => {
	return `${clamp(1 * canvasProps.scale, 1, 2)}px`;
});

const topHandle = computed(() => {
	return {
		width: 16 * canvasProps.scale,
		height: 4 * canvasProps.scale,
		bottom: `calc(-8px * ${canvasProps.scale})`,
		left: `calc(50% - ${8 * canvasProps.scale}px)`,
	};
});

const bottomHandle = computed(() => {
	return {
		width: 16 * canvasProps.scale,
		height: 4 * canvasProps.scale,
		top: `calc(-8px * ${canvasProps.scale})`,
		left: `calc(50% - ${8 * canvasProps.scale}px)`,
	};
});

const leftHandle = computed(() => {
	return {
		width: 4 * canvasProps.scale,
		height: 16 * canvasProps.scale,
		right: `calc(-8px * ${canvasProps.scale})`,
		top: `calc(50% - ${8 * canvasProps.scale}px)`,
	};
});

const rightHandle = computed(() => {
	return {
		width: 4 * canvasProps.scale,
		height: 16 * canvasProps.scale,
		left: `calc(-8px * ${canvasProps.scale})`,
		top: `calc(50% - ${8 * canvasProps.scale}px)`,
	};
});

enum Position {
	Top = "top",
	Right = "right",
	Bottom = "bottom",
	Left = "left",
}

const messageShown = ref(false);

const handlePadding = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	// if (!messageShown.value && !(ev.shiftKey || ev.altKey)) {
	// 	makeToast();
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

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(target).cursor;

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		let movement = 0;
		let affectingAxis = null;
		props.onUpdate && props.onUpdate();
		if (position === Position.Top) {
			movement = Math.max(startTop + mouseMoveEvent.clientY - startY, 0);
			targetBlock.setStyle("paddingTop", movement + "px");
			affectingAxis = "y";
		} else if (position === Position.Bottom) {
			movement = Math.max(startBottom + startY - mouseMoveEvent.clientY, 0);
			targetBlock.setStyle("paddingBottom", movement + "px");
			affectingAxis = "y";
		} else if (position === Position.Left) {
			movement = Math.max(startLeft + mouseMoveEvent.clientX - startX, 0);
			targetBlock.setStyle("paddingLeft", movement + "px");
			affectingAxis = "x";
		} else if (position === Position.Right) {
			movement = Math.max(startRight + startX - mouseMoveEvent.clientX, 0);
			targetBlock.setStyle("paddingRight", movement + "px");
			affectingAxis = "x";
		}

		if (mouseMoveEvent.altKey) {
			if (affectingAxis === "y") {
				targetBlock.setStyle("paddingTop", movement + "px");
				targetBlock.setStyle("paddingBottom", movement + "px");
			} else if (affectingAxis === "x") {
				targetBlock.setStyle("paddingLeft", movement + "px");
				targetBlock.setStyle("paddingRight", movement + "px");
			}
		} else if (mouseMoveEvent.shiftKey) {
			targetBlock.setStyle("paddingTop", movement + "px");
			targetBlock.setStyle("paddingBottom", movement + "px");
			targetBlock.setStyle("paddingLeft", movement + "px");
			targetBlock.setStyle("paddingRight", movement + "px");
		}

		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			updating.value = false;
			mouseUpEvent.preventDefault();
		},
		{ once: true }
	);
};

let makeToast = () =>
	toast({
		text: 'Press "shift" key to apply padding to all sides and "alt" key to apply padding on either sides.',
		timeout: 6,
		position: "bottom-left",
	});
</script>
