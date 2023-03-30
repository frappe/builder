<template>
	<span class="resize-dimensions bg-gray-600 absolute h-8 w-20 justify-center rounded-full text-sm right-[-40px] bottom-[-40px] text-white flex whitespace-nowrap items-center p-2 opacity-80" v-if="resizing">
		{{ parseInt(targetProps.styles.width || 100) }} x {{ parseInt(targetProps.styles.height) }}
	</span>
	<div class="absolute w-[4px] border-none bg-transparent top-0
		bottom-0 left-[-2px] left-handle ew-resize pointer-events-auto">
	</div>
	<div class="absolute w-[4px] border-none bg-transparent top-0
		bottom-0 right-[-2px] right-handle pointer-events-auto" :class="{ 'cursor-ew-resize': true }"
		@mousedown.stop="handleRightResize">
	</div>
	<div class="absolute h-[4px] border-none bg-transparent top-[-2px]
		right-0 left-0 top-handle ns-resize pointer-events-auto">
	</div>
	<div class="absolute h-[4px] border-none bg-transparent bottom-[-2px]
		right-0 left-0 bottom-handle pointer-events-auto" :class="{ 'cursor-ns-resize': true }"
			@mousedown.stop="handleBottomResize">
	</div>
	<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
		bottom-[-4px] right-[-4px] cursor-nwse-resize pointer-events-auto" @mousedown.stop="handleBottomCornerResize">
	</div>
</template>
<script setup>
import { ref, onMounted } from "vue";
import useStore from "../store";
import BlockProperties from "../utils/blockProperties";
import guidesTracker from "../utils/guidesTracker";

const props = defineProps({
	targetProps: {
		type: BlockProperties
	},
	target: {
		type: HTMLElement
	}
});

const store = useStore();
const targetProps = props.targetProps;
const target = props.target;
const resizing = ref(false);
let guides = null;

onMounted(() => {
	guides = guidesTracker(target);
})

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
		const movement = (mouseMoveEvent.clientX - startX) / store.canvas.scale * 2;
		if (mouseMoveEvent.shiftKey) {
			const movementPercent = movement / parentWidth * 100;
			const startWidthPercent = startWidth / parentWidth * 100;
			targetProps.setStyle("width", `${startWidthPercent + movementPercent}%`);
		} else {
			let finalWidth = guides.getFinalWidth(startWidth + movement);
			targetProps.setStyle("width", `${finalWidth}px`);
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
}

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

		targetProps.setStyle("height", `${finalHeight}px`);
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
}

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
		targetProps.setStyle("width", `${startWidth + movementX}px`);
		const movementY = mouseMoveEvent.clientY - startY;
		targetProps.setStyle("height", `${startHeight + movementY}px`);
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
		resizing.value = false;
	});
}
</script>