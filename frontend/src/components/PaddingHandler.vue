<template>
	<div class="opacity-60 group">
		<div class="absolute padding-handler bg-purple-400 w-full cursor-ns-resize flex" :style="{
			height: topPaddingHandlerHeight + 'px',
		}" @mousedown.stop="handlePadding" ref="topPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingTop }}</div> -->
		</div>
		<div class="absolute padding-handler bg-purple-400 bottom-0 w-full cursor-ns-resize flex" :style="{
			height: bottomPaddingHandlerHeight + 'px',
		}" @mousedown.stop="handlePadding" ref="bottomPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingBottom }}</div> -->
		</div>
		<div class="absolute padding-handler bg-purple-400 left-0 h-full cursor-ew-resize flex" :style="{
			width: leftPaddingHandlerWidth + 'px',
		}" @mousedown.stop="handlePadding" ref="leftPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingLeft }}</div> -->
		</div>
		<div class="absolute padding-handler bg-purple-400 right-0 h-full cursor-ew-resize flex" :style="{
			width: rightPaddingHandlerWidth + 'px',
		}" @mousedown.stop="handlePadding" ref="rightPaddingHandler">
			<!-- <div class="m-auto group-hover:block hidden">{{ targetProps.styles.paddingRight }}</div> -->
		</div>
	</div>
</template>
<script setup>
import useStore from '../store';
import { ref, computed } from 'vue';
const props = defineProps(["targetProps"]);

const store = useStore();
const targetProps = props.targetProps;

// Padding handlers
let topPaddingHandler = ref(null);
let bottomPaddingHandler = ref(null);
let leftPaddingHandler = ref(null);
let rightPaddingHandler = ref(null);

const topPaddingHandlerHeight = computed(() => {
	return (parseInt(targetProps.styles.paddingTop, 10) || 5) * store.canvas.scale;
})
const bottomPaddingHandlerHeight = computed(() => {
	return (parseInt(targetProps.styles.paddingBottom, 10) || 5) * store.canvas.scale;
})
const leftPaddingHandlerWidth = computed(() => {
	return (parseInt(targetProps.styles.paddingLeft, 10) || 5) * store.canvas.scale;
})
const rightPaddingHandlerWidth = computed(() => {
	return (parseInt(targetProps.styles.paddingRight, 10) || 5) * store.canvas.scale;
})

const handlePadding = (ev) => {
	const startY = ev.clientY;
	const startX = ev.clientX;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		let movement = 0;

		if (ev.target === topPaddingHandler.value) {
			movement = Math.max(mouseMoveEvent.clientY - startY, 0);
			targetProps.setStyle("paddingTop", movement + "px");
		} else if (ev.target === bottomPaddingHandler.value) {
			movement = Math.max(startY - mouseMoveEvent.clientY, 0);
			targetProps.setStyle("paddingBottom", movement + "px");
		} else if (ev.target === leftPaddingHandler.value) {
			movement = Math.max(mouseMoveEvent.clientX - startX, 0);
			targetProps.setStyle("paddingLeft", movement + "px");
		} else if (ev.target === rightPaddingHandler.value) {
			movement = Math.max(startX - mouseMoveEvent.clientX, 0);
			targetProps.setStyle("paddingRight", movement + "px");
		}

		if (mouseMoveEvent.shiftKey) {
			targetProps.setStyle("paddingTop", movement + "px");
			targetProps.setStyle("paddingBottom", movement + "px");
			targetProps.setStyle("paddingLeft", movement + "px");
			targetProps.setStyle("paddingRight", movement + "px");
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