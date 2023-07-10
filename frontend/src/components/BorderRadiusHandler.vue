<template>
	<div
		class="border-radius-resize pointer-events-auto absolute left-2 top-2 h-[9px] w-[9px] cursor-pointer rounded-full border-[1px] border-blue-400 bg-white"
		:class="{
			hidden: store.canvas.scale < 0.7,
		}"
		@mousedown.stop="handleRounded">
		<div
			class="pointer-events-none absolute left-[2px] top-[2px] h-[3px] w-[3px] rounded-full border-none bg-blue-400">
			<div
				class="absolute left-2 top-2 w-fit rounded-full bg-zinc-800 px-3 py-2 text-xs text-white opacity-60"
				v-show="updating">
				{{ borderRadius }}
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { getNumberFromPx } from "@/utils/helpers";
import { ref } from "vue";
import useStore from "../store";
import Block from "../utils/block";

const store = useStore();
const props = defineProps({
	targetBlock: {
		type: Block,
		required: true,
	},
	target: {
		type: Object,
		required: true,
	},
});

const targetBlock = props.targetBlock;
const target = props.target as HTMLElement;
const borderRadius = ref(parseInt(target.style.borderRadius, 10) || 0);
const updating = ref(false);

const handleRounded = (ev: MouseEvent) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const handle = ev.currentTarget as HTMLElement;
	const handleStyle = window.getComputedStyle(handle);
	let minLeft = 10;
	let minTop = 10;

	const targetBounds = target.getBoundingClientRect();
	const targetStyle = window.getComputedStyle(target);
	const targetWidth = parseInt(targetStyle.width, 10);
	const targetHeight = parseInt(targetStyle.height, 10);
	const handleHeight = parseInt(handleStyle.height, 10);
	const handleWidth = parseInt(handleStyle.width, 10);

	const maxRadius = Math.min(targetHeight, targetWidth) / 2;

	// refer position based on bounding rect of target (target could have been scaled)
	const maxDistance = Math.min(targetBounds.height, targetBounds.width) / 2;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = handle.style.cursor;

	let lastX = startX;
	let lastY = startY;

	updating.value = true;

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		mouseMoveEvent.preventDefault();
		const movementX = mouseMoveEvent.clientX - lastX;
		const movementY = mouseMoveEvent.clientY - lastY;

		// mean of movement on both axis
		const movement = (movementX + movementY) / 2;
		if (movement < 0) {
			minTop = -(handleHeight / 2);
			minLeft = -(handleWidth / 2);
		}
		let radius = Math.round(getNumberFromPx(target.style.borderRadius) + movement);
		radius = Math.max(0, Math.min(radius, maxRadius));

		const ratio = radius / maxRadius;
		const newTop = Math.max(minTop, maxDistance * ratio - handleHeight / 2);
		const newLeft = Math.max(minLeft, maxDistance * ratio - handleWidth / 2);
		borderRadius.value = radius;
		targetBlock.setStyle("borderRadius", `${radius}px`);
		handle.style.top = `${newTop}px`;
		handle.style.left = `${newLeft}px`;

		lastX = mouseMoveEvent.clientX;
		lastY = mouseMoveEvent.clientY;
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			if (getNumberFromPx(targetBlock.getStyle("borderRadius")) < 10) {
				handle.style.top = `${10}px`;
				handle.style.left = `${10}px`;
			}

			updating.value = false;
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			mouseUpEvent.preventDefault();
		},
		{ once: true }
	);
};
</script>
