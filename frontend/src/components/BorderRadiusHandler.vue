<template>
	<CursorTooltip v-if="updating" :position="cursorPosition">{{ borderRadius }}</CursorTooltip>

	<div
		ref="handler"
		class="border-radius-resize pointer-events-auto absolute h-[10px] w-[10px] cursor-pointer rounded-full border-2 border-blue-400 bg-white"
		:class="{
			hidden: !isHandlerVisible,
			'border-purple-400': targetBlock.isExtendedFromComponent(),
		}"
		:style="handlerPosition"
		@mousedown.stop="handleRounded" />
</template>

<script setup lang="ts">
import type Block from "@/block";
import { startDrag } from "@/utils/cursor";
import { getNumberFromPx } from "@/utils/helpers";
import { useElementBounding } from "@vueuse/core";
import type { Ref } from "vue";
import { computed, inject, onMounted, reactive, ref, watchEffect } from "vue";
import CursorTooltip from "./CursorTooltip.vue";

const props = defineProps<{
	targetBlock: Block;
	target: HTMLElement | SVGElement;
}>();

const borderRadius = ref(parseInt(props.target.style.borderRadius, 10) || 0);
const updating = ref(false);
const cursorPosition = ref({ x: 0, y: 0 });
const canvasProps = inject("canvasProps") as CanvasProps;
const handler = ref() as Ref<HTMLElement>;
const handlerTop = ref(10);
const handlerLeft = ref(10);

const MIN_POSITION = { top: 10, left: 10 };
const MIN_TARGET_SIZE = 25;

const targetBounds = reactive(useElementBounding(props.target));
const maxDistance = computed(() => Math.min(targetBounds.width, targetBounds.height) / 2);

const maxRadius = computed(() => {
	props.targetBlock.getStyle("width");
	props.targetBlock.getStyle("height");
	const targetStyle = window.getComputedStyle(props.target);
	return Math.min(parseInt(targetStyle.height, 10), parseInt(targetStyle.width, 10)) / 2;
});

const handlerPosition = computed(() => ({
	top: `${handlerTop.value}px`,
	left: `${handlerLeft.value}px`,
}));

const isHandlerVisible = computed(
	() =>
		canvasProps.scale >= 0.4 &&
		getNumberFromPx(targetBounds.height) >= MIN_TARGET_SIZE &&
		getNumberFromPx(targetBounds.width) >= MIN_TARGET_SIZE,
);

const setHandlerPosition = (radius: number) => {
	if (!handler.value) return;
	const ratio = radius / maxRadius.value;
	const { height, width } = handler.value.getBoundingClientRect();
	handlerTop.value = Math.max(MIN_POSITION.top, maxDistance.value * ratio - height / 2);
	handlerLeft.value = Math.max(MIN_POSITION.left, maxDistance.value * ratio - width / 2);
};

const handleRounded = (ev: MouseEvent) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	let lastX = startX;
	let lastY = startY;
	updating.value = true;
	cursorPosition.value = { x: startX, y: startY };

	const handleDimensions = handler.value.getBoundingClientRect();
	const startRadius = props.targetBlock.getStyle("borderRadius", null, true);
	const startBorderRadius = borderRadius.value;
	const startMinPosition = { ...MIN_POSITION };

	startDrag({
		cursor: window.getComputedStyle(ev.target as HTMLElement).cursor,
		onMove: (mouseMoveEvent) => {
			cursorPosition.value = { x: mouseMoveEvent.clientX, y: mouseMoveEvent.clientY };
			const movementX = mouseMoveEvent.clientX - lastX;
			const movementY = mouseMoveEvent.clientY - lastY;
			const movement = ((movementX + movementY) / 2) * 2;

			if (movement < 0) {
				MIN_POSITION.top = -(handleDimensions.height / 2);
				MIN_POSITION.left = -(handleDimensions.width / 2);
			}

			const radius = Math.round(
				Math.max(0, Math.min(getNumberFromPx(props.target.style.borderRadius) + movement, maxRadius.value)),
			);

			borderRadius.value = radius;
			setHandlerPosition(radius);
			props.targetBlock.setStyle("borderRadius", `${radius}px`);

			lastX = mouseMoveEvent.clientX;
			lastY = mouseMoveEvent.clientY;
		},
		onCancel: () => {
			props.targetBlock.setStyle("borderRadius", startRadius ?? null);
			borderRadius.value = startBorderRadius;
			// onMove drags this below zero to let the handle sit outside the corner
			Object.assign(MIN_POSITION, startMinPosition);
			setHandlerPosition(startBorderRadius);
		},
		onEnd: () => {
			if (getNumberFromPx(props.targetBlock.getStyle("borderRadius") as string) < 10) {
				handlerTop.value = MIN_POSITION.top;
				handlerLeft.value = MIN_POSITION.left;
			}
			updating.value = false;
		},
	});
};

onMounted(() => {
	const radius = Math.max(0, Math.min(borderRadius.value, maxRadius.value));
	borderRadius.value = radius;
	setHandlerPosition(radius);
});

watchEffect(() => {
	props.targetBlock.getStyle("height");
	props.targetBlock.getStyle("width");
	targetBounds.update();
});
</script>
