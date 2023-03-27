<template>
	<div class="opacity-60 group">
		<div class="absolute padding-handler bg-purple-400 w-full flex" :style="{
			height: topPaddingHandlerHeight + 'px',
		}" :class="{
			'cursor-ns-resize': !disableHandlers
		}" @mousedown.stop="handlePadding" ref="topPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingTop }}</div> -->
		</div>
		<div class="absolute padding-handler bg-purple-400 bottom-0 w-full flex" :style="{
			height: bottomPaddingHandlerHeight + 'px',
		}" :class="{
			'cursor-ns-resize': !disableHandlers
		}" @mousedown.stop="handlePadding" ref="bottomPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingBottom }}</div> -->
		</div>
		<div class="absolute padding-handler bg-purple-400 left-0 h-full flex" :style="{
			width: leftPaddingHandlerWidth + 'px',
		}" :class="{
			'cursor-ew-resize': !disableHandlers
		}" @mousedown.stop="handlePadding" ref="leftPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingLeft }}</div> -->
		</div>
		<div class="absolute padding-handler bg-purple-400 right-0 h-full flex" :style="{
			width: rightPaddingHandlerWidth + 'px',
		}" :class="{
			'cursor-ew-resize': !disableHandlers
		}" @mousedown.stop="handlePadding" ref="rightPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingRight }}</div> -->
		</div>
	</div>
</template>
<script setup>
import useStore from '../store';
import { ref, computed } from 'vue';
import BlockProperties from '../utils/blockProperties';
const props = defineProps({
	targetProps: {
		type: BlockProperties,
	},
	disableHandlers: {
		type: Boolean,
		default: false
	}
});

const store = useStore();
const targetProps = props.targetProps;

// Padding handlers
let topPaddingHandler = ref(null);
let bottomPaddingHandler = ref(null);
let leftPaddingHandler = ref(null);
let rightPaddingHandler = ref(null);

const topPaddingHandlerHeight = computed(() => {
	return (parseInt(targetProps.styles.paddingTop, 10)) * store.canvas.scale;
})
const bottomPaddingHandlerHeight = computed(() => {
	return (parseInt(targetProps.styles.paddingBottom, 10)) * store.canvas.scale;
})
const leftPaddingHandlerWidth = computed(() => {
	return (parseInt(targetProps.styles.paddingLeft, 10)) * store.canvas.scale;
})
const rightPaddingHandlerWidth = computed(() => {
	return (parseInt(targetProps.styles.paddingRight, 10)) * store.canvas.scale;
})

const handlePadding = (ev) => {
	if (props.disableHandlers) return;
	const startY = ev.clientY;
	const startX = ev.clientX;

	const startTop = parseInt(targetProps.styles.paddingTop, 10) || 0;
	const startBottom = parseInt(targetProps.styles.paddingBottom, 10) || 0;
	const startLeft = parseInt(targetProps.styles.paddingLeft, 10) || 0;
	const startRight = parseInt(targetProps.styles.paddingRight, 10) || 0;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		let movement = 0;
		let affectingAxis = null;

		if (ev.target === topPaddingHandler.value) {
			movement = Math.max(startTop + mouseMoveEvent.clientY - startY, 0);
			targetProps.setStyle("paddingTop", movement + "px");
			affectingAxis = "y";
		} else if (ev.target === bottomPaddingHandler.value) {
			movement = Math.max(startBottom + startY - mouseMoveEvent.clientY, 0);
			targetProps.setStyle("paddingBottom", movement + "px");
			affectingAxis = "y";
		} else if (ev.target === leftPaddingHandler.value) {
			movement = Math.max(startLeft + mouseMoveEvent.clientX - startX, 0);
			targetProps.setStyle("paddingLeft", movement + "px");
			affectingAxis = "x";
		} else if (ev.target === rightPaddingHandler.value) {
			movement = Math.max(startRight + startX - mouseMoveEvent.clientX, 0);
			targetProps.setStyle("paddingRight", movement + "px");
			affectingAxis = "x";
		}

		if (mouseMoveEvent.shiftKey) {
			if (affectingAxis === "y") {
			targetProps.setStyle("paddingTop", movement + "px");
			targetProps.setStyle("paddingBottom", movement + "px");
			} else if (affectingAxis === "x") {
			targetProps.setStyle("paddingLeft", movement + "px");
			targetProps.setStyle("paddingRight", movement + "px");
			}
		}

		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}
</script>