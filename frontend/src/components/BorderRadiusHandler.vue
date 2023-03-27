<template>
	<div class="absolute border-radius-resize w-[9px] h-[9px] border-[1px] border-blue-400 bg-white rounded-full pointer-events-auto top-2 left-2 cursor-pointer"
		:class="{
			'hidden': store.canvas.scale < 0.6,
		}" @mousedown.stop="handleRounded">
		<div class="absolute w-[3px] h-[3px] bg-blue-400 top-[2px] left-[2px] border-none rounded-full pointer-events-none">
		</div>
	</div>
</template>
<script setup>
import useStore from "../store";
import BlockProperties from "../utils/blockProperties";
const store = useStore();
const props = defineProps({
	targetProps: {
		type: BlockProperties,
	},
	target: {
		type: Object
	}
});

const targetProps = props.targetProps;
const target = props.target;

const handleRounded = (ev) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const handle = ev.currentTarget;
	const handleStyle = window.getComputedStyle(handle);
	const minLeft = 10;
	const minTop = 10;

	const targetBounds = target.getBoundingClientRect();
	const targetStyle = window.getComputedStyle(target);
	const targetWidth = parseInt(targetStyle.width, 10);
	const targetHeight = parseInt(targetStyle.height, 10);

	const maxRadius = Math.min(targetHeight, targetWidth) / 2;

	// refer position based on bounding rect of target (target could have been scaled)
	const maxDistance = Math.min(targetBounds.height, targetBounds.width) / 2;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = handle.style.cursor;

	let lastX = startX;
	let lastY = startY;

	const mousemove = (mouseMoveEvent) => {
		mouseMoveEvent.preventDefault();
		const movementX = (mouseMoveEvent.clientX - lastX);
		const movementY = (mouseMoveEvent.clientY - lastY);

		// mean of movement on both axis
		const movement = (movementX + movementY) / 2;
		let radius = parseInt(target.style.borderRadius || 0, 10) + movement;
		radius = Math.max(0, Math.min(radius, maxRadius))

		const ratio = radius / maxRadius;
		const handleHeight = parseInt(handleStyle.height, 10);
		const handleWidth = parseInt(handleStyle.width, 10);
		const newTop = Math.max(minTop, ((maxDistance * ratio) - handleHeight / 2));
		const newLeft = Math.max(minLeft, ((maxDistance * ratio) - handleWidth / 2));

		targetProps.setStyle("borderRadius", `${radius}px`);
		handle.style.top = `${newTop}px`;
		handle.style.left = `${newLeft}px`;

		lastX = mouseMoveEvent.clientX;
		lastY = mouseMoveEvent.clientY;
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}
</script>