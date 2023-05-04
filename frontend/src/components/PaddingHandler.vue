<template>
	<div class="group" :class="{
		'opacity-40': !updating,
		'opacity-70': updating,
	}" @click.stop>
		<div
			class="padding-handler absolute pointer-events-none flex w-full"
			:style="{
				height: topPaddingHandlerHeight + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="topPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto left-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					bottom: topHandle.bottom,
					left: topHandle.left,
					height: topHandle.height + 'px',
					width: topHandle.width + 'px',
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event, Position.Top)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingTop }}
			</div>
		</div>
		<div
			class="padding-handler absolute pointer-events-none bottom-0 flex w-full"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="bottomPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto left-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					top: bottomHandle.top,
					left: bottomHandle.left,
					height: bottomHandle.height + 'px',
					width: bottomHandle.width + 'px',
				}" :class="{
					'cursor-ns-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event, Position.Bottom)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingBottom }}
			</div>
		</div>
		<div
			class="padding-handler absolute pointer-events-none left-0 flex h-full"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="leftPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto top-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					right: leftHandle.right,
					top: leftHandle.top,
					height: leftHandle.height + 'px',
					width: leftHandle.width + 'px',
				}" :class="{
					'cursor-ew-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event, Position.Left)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingLeft }}
			</div>
		</div>
		<div
			class="padding-handler absolute pointer-events-none right-0 flex h-full"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="rightPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto top-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					left: rightHandle.left,
					top: rightHandle.top,
					height: rightHandle.height + 'px',
					width: rightHandle.width + 'px',
				}" :class="{
					'cursor-ew-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event, Position.Right)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingRight }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "../store";
import { ref, computed, watchEffect } from "vue";
import Block from "../utils/block";
import { getNumberFromPx } from "../utils/helpers";
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

const topPaddingHandlerHeight = computed(() => {
	return (getNumberFromPx(blockStyles.value.paddingTop) || 5) * store.canvas.scale;
});
const bottomPaddingHandlerHeight = computed(() => {
	return (getNumberFromPx(blockStyles.value.paddingBottom) || 5) * store.canvas.scale;
});
const leftPaddingHandlerWidth = computed(() => {
	return (getNumberFromPx(blockStyles.value.paddingLeft) || 5) * store.canvas.scale;
});
const rightPaddingHandlerWidth = computed(() => {
	return (getNumberFromPx(blockStyles.value.paddingRight) || 5) * store.canvas.scale;
});

const topHandle = computed(() => {
	return {
		width: 20 * store.canvas.scale,
		height: 5 * store.canvas.scale,
		bottom: `calc(-8px * ${store.canvas.scale})`,
		left: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});

const bottomHandle = computed(() => {
	return {
		width: 20 * store.canvas.scale,
		height: 5 * store.canvas.scale,
		top: `calc(-8px * ${store.canvas.scale})`,
		left: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});

const leftHandle = computed(() => {
	return {
		width: 5 * store.canvas.scale,
		height: 20 * store.canvas.scale,
		right: `calc(-8px * ${store.canvas.scale})`,
		top: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});

const rightHandle = computed(() => {
	return {
		width: 5 * store.canvas.scale,
		height: 20 * store.canvas.scale,
		left: `calc(-8px * ${store.canvas.scale})`,
		top: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});

enum Position {
	Top = 'top',
	Right = 'right',
	Bottom = 'bottom',
	Left = 'left',
}

const handlePadding = (ev: MouseEvent, position: Position ) => {
	if (props.disableHandlers) return;
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

		if (mouseMoveEvent.shiftKey) {
			if (affectingAxis === "y") {
				targetBlock.setStyle("paddingTop", movement + "px");
				targetBlock.setStyle("paddingBottom", movement + "px");
			} else if (affectingAxis === "x") {
				targetBlock.setStyle("paddingLeft", movement + "px");
				targetBlock.setStyle("paddingRight", movement + "px");
			}
		}

		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		updating.value = false;
		mouseUpEvent.preventDefault();
	}, { once: true });
};
</script>
