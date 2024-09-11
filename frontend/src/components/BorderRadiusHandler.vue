<template>
	<div
		ref="handler"
		class="border-radius-resize pointer-events-auto absolute left-2 top-2 h-[10px] w-[10px] cursor-pointer rounded-full border-2 border-blue-400 bg-white"
		:class="{
			hidden: canvasProps.scale < 0.4 || !showHandler(),
		}"
		:style="{
			top: handlerTop + 'px',
			left: handlerLeft + 'px',
		}"
		@mousedown.stop="handleRounded">
		<div
			class="absolute left-2 top-2 w-fit rounded-full bg-zinc-800 px-3 py-2 text-xs text-white opacity-60"
			v-show="updating">
			{{ borderRadius }}
		</div>
	</div>
</template>
<script setup lang="ts">
import { getNumberFromPx } from "@/utils/helpers";
import { Ref, inject, onMounted, ref } from "vue";
import Block from "../utils/block";

const props = defineProps({
	targetBlock: {
		type: Block,
		required: true,
	},
	target: {
		type: [HTMLElement, SVGElement],
		required: true,
	},
});

const borderRadius = ref(parseInt(props.target.style.borderRadius, 10) || 0);
const updating = ref(false);
const canvasProps = inject("canvasProps") as CanvasProps;
const handler = ref() as Ref<HTMLElement>;
const handlerTop = ref(10);
const handlerLeft = ref(10);

let minLeft = 10;
let minTop = 10;

const handleRounded = (ev: MouseEvent) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const handleStyle = window.getComputedStyle(handler.value);

	const handleHeight = parseInt(handleStyle.height, 10);
	const handleWidth = parseInt(handleStyle.width, 10);

	let lastX = startX;
	let lastY = startY;

	updating.value = true;

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		mouseMoveEvent.preventDefault();
		const movementX = mouseMoveEvent.clientX - lastX;
		const movementY = mouseMoveEvent.clientY - lastY;

		// mean of movement on both axis
		const movement = ((movementX + movementY) / 2) * 2;
		if (movement < 0) {
			minTop = -(handleHeight / 2);
			minLeft = -(handleWidth / 2);
		}
		let radius = Math.round(getNumberFromPx(props.target.style.borderRadius) + movement);
		radius = Math.max(0, Math.min(radius, maxRadius));

		setHandlerPosition(radius);
		borderRadius.value = radius;
		props.targetBlock.setStyle("borderRadius", `${radius}px`);

		lastX = mouseMoveEvent.clientX;
		lastY = mouseMoveEvent.clientY;
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			mouseUpEvent.preventDefault();
			if (getNumberFromPx(props.targetBlock.getStyle("borderRadius")) < 10) {
				handlerTop.value = 10;
				handlerLeft.value = 10;
			}

			updating.value = false;
			document.removeEventListener("mousemove", mousemove);
		},
		{ once: true },
	);
};

const targetStyle = window.getComputedStyle(props.target);
const targetWidth = parseInt(targetStyle.width, 10);
const targetHeight = parseInt(targetStyle.height, 10);
const targetBounds = props.target.getBoundingClientRect();
const maxDistance = Math.min(targetBounds.height, targetBounds.width) / 2;
const maxRadius = Math.min(targetHeight, targetWidth) / 2;

const setHandlerPosition = (radius: number) => {
	// refer position based on bounding rect of target (target could have been scaled)
	const handleStyle = window.getComputedStyle(handler.value);
	const handleHeight = parseInt(handleStyle.height, 10);
	const handleWidth = parseInt(handleStyle.width, 10);
	const ratio = radius / maxRadius;
	handlerTop.value = Math.max(minTop, maxDistance * ratio - handleHeight / 2);
	handlerLeft.value = Math.max(minLeft, maxDistance * ratio - handleWidth / 2);
};

const showHandler = () => {
	canvasProps.scale;
	props.targetBlock.getStyle("height");
	props.targetBlock.getStyle("width");
	const targetBounds = props.target.getBoundingClientRect();
	return getNumberFromPx(targetBounds.height) >= 25 && getNumberFromPx(targetBounds.width) >= 25;
};

onMounted(() => {
	setHandlerPosition(borderRadius.value);
});
</script>
