<template>
	<span
		class="resize-dimensions absolute right-[-40px] bottom-[-40px] flex h-8 w-20 items-center justify-center whitespace-nowrap rounded-full bg-gray-600 p-2 text-sm text-white opacity-80"
		v-if="resizing">
		{{ parseInt(targetBlock.styles.width || 100) }} x
		{{ parseInt(targetBlock.styles.height) }}
	</span>
	<div
		class="left-handle ew-resize pointer-events-auto absolute top-0 bottom-0 left-[-2px] w-[4px] border-none bg-transparent" />
	<div
		class="right-handle pointer-events-auto absolute top-0 bottom-0 right-[-2px] w-[4px] border-none bg-transparent"
		:class="{ 'cursor-ew-resize': true }"
		@mousedown.stop="handleRightResize" />
	<div
		class="top-handle ns-resize pointer-events-auto absolute top-[-2px] right-0 left-0 h-[4px] border-none bg-transparent" />
	<div
		class="bottom-handle pointer-events-auto absolute bottom-[-2px] right-0 left-0 h-[4px] border-none bg-transparent"
		:class="{ 'cursor-ns-resize': true }"
		@mousedown.stop="handleBottomResize" />
	<div
		class="pointer-events-auto absolute bottom-[-4px] right-[-4px] h-[8px] w-[8px] cursor-nwse-resize rounded-full border-[1px] border-blue-400 bg-white"
		@mousedown.stop="handleBottomCornerResize" />
</template>
<script setup>
import { ref, onMounted, watchEffect } from "vue";
import useStore from "../store";
import Block from "../utils/block";
import guidesTracker from "../utils/guidesTracker";

const props = defineProps({
	targetBlock: {
		type: Block,
		default: null,
	},
	target: {
		type: HTMLElement,
		default: null,
	},
});

const emit = defineEmits(["resizing"]);
const store = useStore();
const targetBlock = props.targetBlock;
const target = props.target;
const resizing = ref(false);
let guides = null;

onMounted(() => {
	guides = guidesTracker(target);
});

watchEffect(() => {
	emit("resizing", resizing.value);
});

const handleRightResize = (ev) => {
	const startX = ev.clientX;
	const startWidth = target.offsetWidth;
	const parentWidth = target.parentElement.offsetWidth;
	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;
	resizing.value = true;
	guides.showX();
	const mousemove = (mouseMoveEvent) => {
		// movement / scale * speed
		const movement = ((mouseMoveEvent.clientX - startX) / store.canvas.scale) * 2;
		if (mouseMoveEvent.shiftKey) {
			const movementPercent = (movement / parentWidth) * 100;
			const startWidthPercent = (startWidth / parentWidth) * 100;
			const finalHeight = Math.round(startWidthPercent + movementPercent);
			targetBlock.setStyle("width", `${finalHeight}%`);
		} else {
			let finalWidth = guides.getFinalWidth(startWidth + movement);
			targetBlock.setStyle("width", `${finalWidth}px`);
		}
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
		resizing.value = false;
		guides.hideX();
	});
};

const handleBottomResize = (ev) => {
	const startY = ev.clientY;
	const startHeight = target.offsetHeight;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;
	resizing.value = true;
	guides.showY();

	const mousemove = (mouseMoveEvent) => {
		const movement = (mouseMoveEvent.clientY - startY) / store.canvas.scale;
		let finalHeight = guides.getFinalHeight(startHeight + movement);

		targetBlock.setStyle("height", `${finalHeight}px`);
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
		resizing.value = false;
		guides.hideY();
	});
};

const handleBottomCornerResize = (ev) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startHeight = target.offsetHeight;
	const startWidth = target.offsetWidth;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;
	resizing.value = true;

	const mousemove = (mouseMoveEvent) => {
		const movementX = mouseMoveEvent.clientX - startX;
		const finalWidth = Math.round(startWidth + movementX);
		targetBlock.setStyle("width", `${finalWidth}px`);
		const movementY = mouseMoveEvent.clientY - startY;
		const finalHeight = Math.round(startHeight + movementY);
		targetBlock.setStyle("height", `${finalHeight}px`);
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
		resizing.value = false;
	});
};
</script>
