<template>
	<span
		class="resize-dimensions absolute bottom-[-40px] right-[-40px] flex h-8 w-20 items-center justify-center whitespace-nowrap rounded-full bg-gray-600 p-2 text-sm text-white opacity-80"
		v-if="resizing && !props.targetBlock.isText()">
		{{ targetWidth }} x
		{{ targetHeight }}
	</span>
	<span
		class="resize-dimensions absolute bottom-[-40px] right-[-40px] flex h-8 w-fit items-center justify-center whitespace-nowrap rounded-full bg-gray-600 p-2 text-sm text-white opacity-80"
		v-if="resizing && props.targetBlock.isText()">
		{{ fontSize }}
	</span>

	<div
		class="left-handle ew-resize pointer-events-auto absolute bottom-0 left-[-2px] top-0 w-2 border-none bg-transparent" />
	<div
		class="right-handle pointer-events-auto absolute bottom-0 right-[-2px] top-0 w-2 border-none bg-transparent"
		:class="{ 'cursor-ew-resize': true }"
		@mousedown.stop="handleRightResize" />
	<div
		class="top-handle ns-resize pointer-events-auto absolute left-0 right-0 top-[-2px] h-2 border-none bg-transparent" />
	<div
		class="bottom-handle pointer-events-auto absolute bottom-[-2px] left-0 right-0 h-2 border-none bg-transparent"
		:class="{ 'cursor-ns-resize': true }"
		@mousedown.stop="handleBottomResize" />
	<div
		class="pointer-events-auto absolute bottom-[-5px] right-[-5px] h-[12px] w-[12px] cursor-nwse-resize rounded-full border-[2.5px] border-blue-400 bg-white"
		@mousedown.stop="handleBottomCornerResize" />
</template>
<script setup lang="ts">
import { getNumberFromPx } from "@/utils/helpers";
import { clamp } from "@vueuse/core";
import { computed, inject, onMounted, ref, watch } from "vue";
import useStore from "../store";
import Block from "../utils/block";
import guidesTracker from "../utils/guidesTracker";

const props = defineProps({
	targetBlock: {
		type: Block,
		default: null,
	},
	target: {
		type: [HTMLElement, SVGElement],
		default: null,
	},
});

const emit = defineEmits(["resizing"]);
const store = useStore();
const resizing = ref(false);
let guides = null as unknown as ReturnType<typeof guidesTracker>;

const canvasProps = inject("canvasProps") as CanvasProps;

onMounted(() => {
	guides = guidesTracker(props.target as HTMLElement, canvasProps);
});

watch(resizing, () => {
	if (resizing.value) {
		store.activeCanvas?.history.pause();
	} else {
		store.activeCanvas?.history.resume(true);
	}
});

const targetWidth = computed(() => {
	props.targetBlock.getStyle("width"); // to trigger reactivity
	return Math.round(getNumberFromPx(getComputedStyle(props.target).getPropertyValue("width")));
});

const targetHeight = computed(() => {
	props.targetBlock.getStyle("height"); // to trigger reactivity
	return Math.round(getNumberFromPx(getComputedStyle(props.target).getPropertyValue("height")));
});

const fontSize = computed(() => {
	props.targetBlock.getStyle("fontSize"); // to trigger reactivity
	return Math.round(getNumberFromPx(getComputedStyle(props.target).getPropertyValue("font-size")));
});

const handleRightResize = (ev: MouseEvent) => {
	const startX = ev.clientX;
	const startWidth = props.target.offsetWidth;
	const parentWidth = props.target.parentElement?.offsetWidth || 0;
	const startFontSize = fontSize.value;
	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target as HTMLElement).cursor;
	resizing.value = true;
	guides.showX();
	const mousemove = (mouseMoveEvent: MouseEvent) => {
		// movement / scale * speed
		const movement = (mouseMoveEvent.clientX - startX) / canvasProps.scale;
		const finalWidth = Math.abs(guides.getFinalWidth(startWidth + movement));
		if (props.targetBlock.isText() && !mouseMoveEvent.shiftKey) {
			const fontSize = clamp(Math.round(startFontSize + 0.5 * movement), 10, 150);
			props.targetBlock.setStyle("fontSize", `${fontSize}px`);
			return mouseMoveEvent.preventDefault();
		}

		if (props.targetBlock.isSVG()) {
			props.targetBlock.setStyle("width", `${finalWidth}px`);
			props.targetBlock.setStyle("height", `${finalWidth}px`);
		} else if (mouseMoveEvent.shiftKey) {
			const movementPercent = (movement / parentWidth) * 100;
			const startWidthPercent = (startWidth / parentWidth) * 100;
			const finalWidth = Math.abs(Math.round(startWidthPercent + movementPercent));
			props.targetBlock.setStyle("width", `${finalWidth}%`);
		} else {
			props.targetBlock.setStyle("width", `${finalWidth}px`);
		}
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			mouseUpEvent.preventDefault();
			resizing.value = false;
			guides.hideX();
		},
		{ once: true }
	);
};

const handleBottomResize = (ev: MouseEvent) => {
	const startY = ev.clientY;
	const startHeight = props.target.offsetHeight;
	const startFontSize = fontSize.value || 0;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target as HTMLElement).cursor;
	resizing.value = true;
	guides.showY();

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		const movement = (mouseMoveEvent.clientY - startY) / canvasProps.scale;
		let finalHeight = Math.round(Math.abs(guides.getFinalHeight(startHeight + movement)));

		if (props.targetBlock.isText() && !mouseMoveEvent.shiftKey) {
			const fontSize = clamp(Math.round(startFontSize + 0.5 * movement), 10, 300);
			props.targetBlock.setStyle("fontSize", `${fontSize}px`);
			return mouseMoveEvent.preventDefault();
		}

		if (props.targetBlock.isSVG()) {
			props.targetBlock.setStyle("width", `${finalHeight}px`);
			props.targetBlock.setStyle("height", `${finalHeight}px`);
		} else {
			props.targetBlock.setStyle("height", `${finalHeight}px`);
		}

		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			mouseUpEvent.preventDefault();
			resizing.value = false;
			guides.hideY();
		},
		{ once: true }
	);
};

const handleBottomCornerResize = (ev: MouseEvent) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startHeight = props.target.offsetHeight;
	const startWidth = props.target.offsetWidth;
	const startFontSize = fontSize.value || 0;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target as HTMLElement).cursor;
	resizing.value = true;

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		const movementX = (mouseMoveEvent.clientX - startX) / canvasProps.scale;
		const finalWidth = Math.round(startWidth + movementX);

		if (props.targetBlock.isText() && !mouseMoveEvent.shiftKey) {
			const fontSize = clamp(Math.round(startFontSize + 0.5 * movementX), 10, 300);
			props.targetBlock.setStyle("fontSize", `${fontSize}px`);
			return mouseMoveEvent.preventDefault();
		}

		if (mouseMoveEvent.shiftKey || props.targetBlock.isSVG()) {
			props.targetBlock.setStyle("width", `${finalWidth}px`);
			props.targetBlock.setStyle("height", `${finalWidth}px`);
		} else {
			props.targetBlock.setStyle("width", `${finalWidth}px`);
			const movementY = (mouseMoveEvent.clientY - startY) / canvasProps.scale;
			const finalHeight = Math.round(startHeight + movementY);
			props.targetBlock.setStyle("height", `${finalHeight}px`);
			mouseMoveEvent.preventDefault();
		}
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			mouseUpEvent.preventDefault();
			resizing.value = false;
		},
		{ once: true }
	);
};
</script>
