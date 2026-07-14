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
		class="left-handle pointer-events-auto absolute bottom-0 left-[-2px] top-0 w-2 border-none bg-transparent"
		:style="{ cursor: horizontalCursor }"
		@mousedown.stop="(ev) => handleResize(ev, -1, 0)" />
	<div
		class="right-handle pointer-events-auto absolute bottom-0 right-[-2px] top-0 w-2 border-none bg-transparent"
		:style="{ cursor: horizontalCursor }"
		@mousedown.stop="(ev) => handleResize(ev, 1, 0)" />
	<div
		class="top-handle pointer-events-auto absolute left-0 right-0 top-[-2px] h-2 border-none bg-transparent"
		:style="{ cursor: verticalCursor }"
		@mousedown.stop="(ev) => handleResize(ev, 0, -1)" />
	<div
		class="bottom-handle pointer-events-auto absolute bottom-[-2px] left-0 right-0 h-2 border-none bg-transparent"
		:style="{ cursor: verticalCursor }"
		@mousedown.stop="(ev) => handleResize(ev, 0, 1)" />
	<div
		v-for="corner in corners"
		:key="corner.name"
		class="pointer-events-auto absolute h-[12px] w-[12px] rounded-full border-[2.5px] border-blue-400 bg-white"
		:class="[corner.positionClass, { 'border-purple-400': targetBlock.isExtendedFromComponent() }]"
		:style="{ cursor: corner.cursor.value }"
		v-show="!resizing"
		@mousedown.stop.prevent="(ev) => handleResize(ev, corner.horizontal, corner.vertical)" />
</template>
<script setup lang="ts">
import type Block from "@/block";
import resizeCursorSvg from "@/assets/resize-cursor.svg?raw";
import useCanvasStore from "@/stores/canvasStore";
import { clearDragCursor, getRotatedCursor, setDragCursor } from "@/utils/cursor";
import { getTotalRotation, toLocalDelta } from "@/utils/elementRotation";
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

// the block's *rendered* angle, including any rotated ancestors, not just its own style -
// keeps each handle's cursor and the resize-axis projection correct when nested
const rotation = computed(() => getTotalRotation(props.target as Element, props.targetBlock));
const horizontalCursor = computed(() => getRotatedCursor(resizeCursorSvg, rotation.value, "ew-resize"));
const verticalCursor = computed(() => getRotatedCursor(resizeCursorSvg, rotation.value + 90, "ns-resize"));
// top-left/bottom-right share one diagonal (nwse), top-right/bottom-left the other (nesw)
const cornerCursorNWSE = computed(() =>
	getRotatedCursor(resizeCursorSvg, rotation.value + 45, "nwse-resize"),
);
const cornerCursorNESW = computed(() =>
	getRotatedCursor(resizeCursorSvg, rotation.value - 45, "nesw-resize"),
);

const corners = [
	{
		name: "top-left",
		horizontal: -1,
		vertical: -1,
		positionClass: "top-[-5px] left-[-5px]",
		cursor: cornerCursorNWSE,
	},
	{
		name: "top-right",
		horizontal: 1,
		vertical: -1,
		positionClass: "top-[-5px] right-[-5px]",
		cursor: cornerCursorNESW,
	},
	{
		name: "bottom-left",
		horizontal: -1,
		vertical: 1,
		positionClass: "bottom-[-5px] left-[-5px]",
		cursor: cornerCursorNESW,
	},
	{
		name: "bottom-right",
		horizontal: 1,
		vertical: 1,
		positionClass: "bottom-[-5px] right-[-5px]",
		cursor: cornerCursorNWSE,
	},
] as const;

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

// horizontal/vertical: -1 = left/top edge or corner, 1 = right/bottom, 0 = not resized on that axis.
// For the -1 side, the opposite edge is kept visually fixed by shifting top/left the same
// amount the block grew (only meaningful for absolute/fixed blocks, which own their position).
const handleResize = (ev: MouseEvent, horizontal: -1 | 0 | 1, vertical: -1 | 0 | 1) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const target = props.target as HTMLElement;
	const startHeight = target.offsetHeight;
	const startWidth = target.offsetWidth;
	const startTop = target.offsetTop;
	const startLeft = target.offsetLeft;
	const blockStartWidth = props.targetBlock.getStyle("width") as string;
	const blockStartHeight = props.targetBlock.getStyle("height") as string;
	const startFontSize = fontSize.value || 0;
	const canReposition = props.targetBlock.isMovable();

	setDragCursor(window.getComputedStyle(ev.target as HTMLElement).cursor);
	resizing.value = true;
	if (horizontal) guides.showX();
	if (vertical) guides.showY();

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		const dx = (mouseMoveEvent.clientX - startX) / canvasProps.scale;
		const dy = (mouseMoveEvent.clientY - startY) / canvasProps.scale;
		const { x: localX, y: localY } = toLocalDelta(dx, dy, rotation.value);

		if (props.targetBlock.isText() && !props.targetBlock.hasChildren()) {
			setFontSize(vertical ? vertical * localY : horizontal * localX, startFontSize);
			return mouseMoveEvent.preventDefault();
		}

		let widthMovement = horizontal * localX;
		let heightMovement = vertical * localY;
		if (mouseMoveEvent.shiftKey) {
			if (horizontal) heightMovement = widthMovement;
			else if (vertical) widthMovement = heightMovement;
		}

		if (horizontal) setWidth(widthMovement, startWidth, blockStartWidth);
		if (vertical) setHeight(heightMovement, startHeight, blockStartHeight);

		if (canReposition) {
			if (horizontal === -1) props.targetBlock.setStyle("left", `${Math.round(startLeft - widthMovement)}px`);
			if (vertical === -1) props.targetBlock.setStyle("top", `${Math.round(startTop - heightMovement)}px`);
		}

		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			clearDragCursor();
			document.removeEventListener("mousemove", mousemove);
			mouseUpEvent.preventDefault();
			resizing.value = false;
			if (horizontal) guides.hideX();
			if (vertical) guides.hideY();
		},
		{ once: true },
	);
};

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
