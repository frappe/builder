<template>
	<div
		class="border-radius-resize pointer-events-auto absolute top-2 left-2 h-[9px] w-[9px] cursor-pointer rounded-full border-[1px] border-blue-400 bg-white"
		:class="{
			hidden: store.canvas.scale < 0.7,
		}"
		@mousedown.stop="handleRounded">
		<div class="pointer-events-none absolute top-[2px] left-[2px] h-[3px] w-[3px] rounded-full border-none bg-blue-400">
			<div
				class="absolute top-2 left-2 w-fit rounded-full bg-slate-800 py-1 px-3 text-sm text-white opacity-70"
				v-if="updating">
				{{ borderRadius }}
			</div>
		</div>
	</div>
</template>
<script setup>
import useStore from "../store";
import BlockProperties from "../utils/blockProperties";
import { ref } from "vue";

const store = useStore();
const props = defineProps({
	targetProps: {
		type: BlockProperties,
		required: true,
	},
	target: {
		type: Object,
		required: true,
	},
});

const targetProps = props.targetProps;
const target = props.target;
const borderRadius = ref(parseInt(target.style.borderRadius, 10) || 0);
const updating = ref(false);

const handleRounded = (ev) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const handle = ev.currentTarget;
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

	const mousemove = (mouseMoveEvent) => {
		mouseMoveEvent.preventDefault();
		const movementX = mouseMoveEvent.clientX - lastX;
		const movementY = mouseMoveEvent.clientY - lastY;

		// mean of movement on both axis
		const movement = (movementX + movementY) / 2;
		if (movement < 0) {
			minTop = -(handleHeight / 2);
			minLeft = -(handleWidth / 2);
		}
		let radius = Math.round(parseInt(target.style.borderRadius || 0, 10) + movement);
		radius = Math.max(0, Math.min(radius, maxRadius));

		const ratio = radius / maxRadius;
		const newTop = Math.max(minTop, maxDistance * ratio - handleHeight / 2);
		const newLeft = Math.max(minLeft, maxDistance * ratio - handleWidth / 2);
		borderRadius.value = radius;
		targetProps.setStyle("borderRadius", `${radius}px`);
		handle.style.top = `${newTop}px`;
		handle.style.left = `${newLeft}px`;

		lastX = mouseMoveEvent.clientX;
		lastY = mouseMoveEvent.clientY;
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		if (parseInt(targetProps.getStyle("borderRadius"), 10) < 10) {
			handle.style.top = `${10}px`;
			handle.style.left = `${10}px`;
		}

		updating.value = false;
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
};
</script>
