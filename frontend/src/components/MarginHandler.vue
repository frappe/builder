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
			:class="{
				'bg-transparent': !updating,
				'bg-yellow-200': updating,
			}"
			ref="topMarginHandler">
			<div
				class="pointer-events-auto absolute left-[50%] rounded-full border-2 border-yellow-500 bg-yellow-400 hover:scale-110"
				:style="{
					borderWidth: handleBorderWidth,
					bottom: topHandle.bottom,
					left: topHandle.left,
					height: topHandle.height + 'px',
					width: topHandle.width + 'px',
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
				}"
				@mousedown.stop="handleMargin($event, Position.Top)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.marginTop }}
			</div>
		</div>
		<div
			class="margin-handler pointer-events-none absolute bottom-0 flex w-full"
			:style="{
				height: bottomMarginHandlerHeight + 'px',
				bottom: `calc(0% - ${bottomMarginHandlerHeight}px)`,
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-yellow-200': updating,
			}"
			ref="bottomMarginHandler">
			<div
				class="pointer-events-auto absolute left-[50%] rounded-full border-2 border-yellow-500 bg-yellow-400 hover:scale-110"
				:style="{
					borderWidth: handleBorderWidth,
					bottom: bottomHandle.bottom,
					left: bottomHandle.left,
					height: bottomHandle.height + 'px',
					width: bottomHandle.width + 'px',
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
				}"
				@mousedown.stop="handleMargin($event, Position.Bottom)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.marginBottom }}
			</div>
		</div>
		<div
			class="margin-handler pointer-events-none absolute left-0 flex h-full"
			:style="{
				width: leftMarginHandlerWidth + 'px',
				left: `calc(0% - ${leftMarginHandlerWidth}px)`,
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-yellow-200': updating,
			}"
			ref="leftMarginHandler">
			<div
				class="pointer-events-auto absolute top-[50%] rounded-full border-2 border-yellow-500 bg-yellow-400 hover:scale-110"
				:style="{
					borderWidth: handleBorderWidth,
					right: leftHandle.right,
					top: leftHandle.top,
					height: leftHandle.height + 'px',
					width: leftHandle.width + 'px',
				}"
				:class="{
					'cursor-ew-resize': !disableHandlers,
				}"
				@mousedown.stop="handleMargin($event, Position.Left)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.marginLeft }}
			</div>
		</div>
		<div
			class="margin-handler pointer-events-none absolute right-0 flex h-full"
			:style="{
				width: rightMarginHandlerWidth + 'px',
				right: `calc(0% - ${rightMarginHandlerWidth}px)`,
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-yellow-200': updating,
			}"
			ref="rightMarginHandler">
			<div
				class="pointer-events-auto absolute top-[50%] rounded-full border-2 border-yellow-500 bg-yellow-400 hover:scale-110"
				:style="{
					borderWidth: handleBorderWidth,
					right: rightHandle.right,
					top: rightHandle.top,
					height: rightHandle.height + 'px',
					width: rightHandle.width + 'px',
				}"
				:class="{
					'cursor-ew-resize': !disableHandlers,
				}"
				@mousedown.stop="handleMargin($event, Position.Right)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.marginRight }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { computed, ref, watchEffect } from "vue";
import useStore from "../store";
import Block from "../utils/block";
import { getNumberFromPx } from "../utils/helpers";
import { clamp } from "@vueuse/core";
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

const store = useStore();
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

const topMarginHandlerHeight = computed(() => {
	return (getNumberFromPx(blockStyles.value.marginTop) || 0) * store.canvas.scale;
});
const bottomMarginHandlerHeight = computed(() => {
	return (getNumberFromPx(blockStyles.value.marginBottom) || 0) * store.canvas.scale;
});
const leftMarginHandlerWidth = computed(() => {
	return (getNumberFromPx(blockStyles.value.marginLeft) || 0) * store.canvas.scale;
});
const rightMarginHandlerWidth = computed(() => {
	return (getNumberFromPx(blockStyles.value.marginRight) || 0) * store.canvas.scale;
});

const handleBorderWidth = computed(() => {
	return `${clamp(1 * store.canvas.scale, 1, 2)}px`;
});

const topHandle = computed(() => {
	return {
		width: 16 * store.canvas.scale,
		height: 4 * store.canvas.scale,
		bottom: `calc(4px * ${store.canvas.scale})`,
		left: `calc(50% - ${8 * store.canvas.scale}px)`,
	};
});

const bottomHandle = computed(() => {
	return {
		width: 16 * store.canvas.scale,
		height: 4 * store.canvas.scale,
		bottom: `calc(-8px * ${store.canvas.scale})`,
		left: `calc(50% - ${8 * store.canvas.scale}px)`,
	};
});

const leftHandle = computed(() => {
	return {
		width: 4 * store.canvas.scale,
		height: 16 * store.canvas.scale,
		right: `calc(4px * ${store.canvas.scale})`,
		top: `calc(50% - ${8 * store.canvas.scale}px)`,
	};
});

const rightHandle = computed(() => {
	return {
		width: 4 * store.canvas.scale,
		height: 16 * store.canvas.scale,
		right: `calc(-8px * ${store.canvas.scale})`,
		top: `calc(50% - ${8 * store.canvas.scale}px)`,
	};
});

enum Position {
	Top = "top",
	Right = "right",
	Bottom = "bottom",
	Left = "left",
}

const handleMargin = (ev: MouseEvent, position: Position) => {
	if (props.disableHandlers) return;
	updating.value = true;
	const startY = ev.clientY;
	const startX = ev.clientX;
	const target = ev.target as HTMLElement;

	const startTop = getNumberFromPx(blockStyles.value.marginTop) || 0;
	const startBottom = getNumberFromPx(blockStyles.value.marginBottom) || 0;
	const startLeft = getNumberFromPx(blockStyles.value.marginLeft) || 0;
	const startRight = getNumberFromPx(blockStyles.value.marginRight) || 0;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(target).cursor;

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		let movement = 0;
		let affectingAxis = null;
		props.onUpdate && props.onUpdate();
		if (position === Position.Top) {
			movement = Math.max(startTop + mouseMoveEvent.clientY - startY, 0);
			targetBlock.setStyle("marginTop", movement + "px");
			affectingAxis = "y";
		} else if (position === Position.Bottom) {
			movement = Math.max(startBottom + mouseMoveEvent.clientY - startY, 0);
			targetBlock.setStyle("marginBottom", movement + "px");
			affectingAxis = "y";
		} else if (position === Position.Left) {
			movement = Math.max(startLeft + mouseMoveEvent.clientX - startX, 0);
			targetBlock.setStyle("marginLeft", movement + "px");
			affectingAxis = "x";
		} else if (position === Position.Right) {
			movement = Math.max(startRight + mouseMoveEvent.clientX - startX, 0);
			targetBlock.setStyle("marginRight", movement + "px");
			affectingAxis = "x";
		}

		if (mouseMoveEvent.shiftKey) {
			if (affectingAxis === "y") {
				targetBlock.setStyle("marginTop", movement + "px");
				targetBlock.setStyle("marginBottom", movement + "px");
			} else if (affectingAxis === "x") {
				targetBlock.setStyle("marginLeft", movement + "px");
				targetBlock.setStyle("marginRight", movement + "px");
			}
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
</script>
