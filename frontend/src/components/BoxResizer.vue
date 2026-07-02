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
		:class="{
			'border-purple-400': targetBlock.isExtendedFromComponent(),
		}"
		v-show="!resizing"
		@mousedown.stop.prevent="handleBottomCornerResize" />
</template>
<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { getComputedStyleFor, startCanvasDrag } from "@/utils/canvasFrameDom";
import { getNumberFromPx } from "@/utils/helpers";
import { clamp } from "@vueuse/core";
import { computed, inject, onMounted, ref, watch } from "vue";
import guidesTracker from "../utils/guidesTracker";

const canvasStore = useCanvasStore();
const props = defineProps<{
	targetBlock: Block;
	target: HTMLElement | SVGElement;
}>();

const emit = defineEmits(["resizing"]);
const resizing = ref(false);
let guides = null as unknown as ReturnType<typeof guidesTracker>;

const canvasProps = inject("canvasProps") as CanvasProps;

onMounted(() => {
	guides = guidesTracker(props.target as HTMLElement, canvasProps);
});

watch(resizing, () => {
	if (resizing.value) {
		if (canvasStore.activeCanvas) {
			canvasStore.activeCanvas.history?.pause();
			canvasStore.activeCanvas.resizingBlock = true;
		}
		emit("resizing", true);
	} else {
		if (canvasStore.activeCanvas) {
			canvasStore.activeCanvas?.history?.resume(undefined, true, true);
			canvasStore.activeCanvas.resizingBlock = false;
		}
		emit("resizing", false);
	}
});

const targetWidth = computed(() => {
	props.targetBlock.getStyle("width"); // to trigger reactivity
	return Math.round(getNumberFromPx(getComputedStyleFor(props.target).getPropertyValue("width")));
});

const targetHeight = computed(() => {
	props.targetBlock.getStyle("height"); // to trigger reactivity
	return Math.round(getNumberFromPx(getComputedStyleFor(props.target).getPropertyValue("height")));
});

const fontSize = computed(() => {
	props.targetBlock.getStyle("fontSize"); // to trigger reactivity
	return Math.round(getNumberFromPx(getComputedStyleFor(props.target).getPropertyValue("font-size")));
});

type ResizeDirection = "right" | "bottom" | "corner";

const startResize = (ev: MouseEvent, direction: ResizeDirection) => {
	const startHeight = (props.target as HTMLElement).offsetHeight;
	const startWidth = (props.target as HTMLElement).offsetWidth;
	const blockStartWidth = props.targetBlock.getStyle("width") as string;
	const blockStartHeight = props.targetBlock.getStyle("height") as string;
	const startFontSize = fontSize.value || 0;

	resizing.value = true;
	if (direction === "right") guides.showX();
	if (direction === "bottom") guides.showY();

	startCanvasDrag(ev, props.target, {
		cursor: getComputedStyleFor(ev.target as Element).cursor,
		onMove: ({ event, movementX, movementY }) => {
			const primaryMovement = direction === "right" ? movementX : movementY;
			if (props.targetBlock.isText() && !props.targetBlock.hasChildren()) {
				setFontSize(primaryMovement, startFontSize);
				event.preventDefault();
				return;
			}

			if (direction !== "bottom") {
				setWidth(movementX, startWidth, blockStartWidth);
			}
			if (direction !== "right") {
				setHeight(
					direction === "corner" && event.shiftKey ? movementX : movementY,
					startHeight,
					blockStartHeight,
				);
			}
			if (direction === "right" && event.shiftKey) {
				setHeight(movementX, startHeight, blockStartHeight);
			}
			if (direction === "bottom" && event.shiftKey) {
				setWidth(movementY, startWidth, blockStartWidth);
			}
			event.preventDefault();
		},
		onEnd: (event) => {
			event.preventDefault();
			resizing.value = false;
			if (direction === "right") guides.hideX();
			if (direction === "bottom") guides.hideY();
		},
	});
};

const handleRightResize = (ev: MouseEvent) => startResize(ev, "right");
const handleBottomResize = (ev: MouseEvent) => startResize(ev, "bottom");
const handleBottomCornerResize = (ev: MouseEvent) => startResize(ev, "corner");

const setWidth = (movementX: number, startWidth: number, blockStartWidth: string) => {
	const finalWidth = Math.round(startWidth + movementX);
	if (blockStartWidth?.includes("%")) {
		const parentWidth = props.target.parentElement?.offsetWidth || 0;
		const movementPercent = (movementX / parentWidth) * 100;
		const startWidthPercent = (startWidth / parentWidth) * 100;
		const finalWidthPercent = Math.abs(Math.round(startWidthPercent + movementPercent));
		props.targetBlock.setStyle("width", `${finalWidthPercent}%`);
	} else {
		props.targetBlock.setStyle("width", `${finalWidth}px`);
	}
};

const setHeight = (movementY: number, startHeight: number, blockStartHeight: string) => {
	const finalHeight = Math.round(startHeight + movementY);
	if (blockStartHeight?.includes("%")) {
		const parentHeight = props.target.parentElement?.offsetHeight || 0;
		const movementPercent = (movementY / parentHeight) * 100;
		const startHeightPercent = (startHeight / parentHeight) * 100;
		const finalHeightPercent = Math.abs(Math.round(startHeightPercent + movementPercent));
		props.targetBlock.setStyle("height", `${finalHeightPercent}%`);
	} else {
		props.targetBlock.setStyle("height", `${finalHeight}px`);
	}
};

const setFontSize = (movement: number, startFontSize: number) => {
	const fontSize = clamp(Math.round(startFontSize + 0.5 * movement), 10, 300);
	props.targetBlock.setStyle("fontSize", `${fontSize}px`);
};
</script>
