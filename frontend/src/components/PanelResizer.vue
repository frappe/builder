<template>
	<div
		class="absolute z-20"
		:class="{
			'top-0 h-full w-1 hover:cursor-ew-resize': side === 'left' || side === 'right',
			'left-0 right-0 h-1 hover:cursor-ns-resize': side === 'top' || side === 'bottom',
			'left-0': side === 'left',
			'right-0': side === 'right',
			'top-0': side === 'top',
			'bottom-0': side === 'bottom',
			'bg-surface-gray-3': dragActive,
		}"
		@mousedown.prevent="resize">
		<slot />
	</div>
</template>
<script setup lang="ts">
import { ref } from "vue";
const props = withDefaults(
	defineProps<{
		maxDimension?: number;
		minDimension?: number;
		dimension?: number;
		side?: "left" | "right" | "top" | "bottom";
		resizeSensitivity?: number;
	}>(),
	{
		maxDimension: 350,
		minDimension: 280,
		dimension: 300,
		side: "right",
		resizeSensitivity: 1,
	},
);

const emit = defineEmits({
	resize: (width) => width,
});

const dragActive = ref(false);

defineExpose({ dragActive });

function resize(ev: MouseEvent) {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startDimension = props.dimension;
	const target = ev.target as HTMLElement;
	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(target).cursor;

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		let movement = 0;
		if (["top", "bottom"].includes(props.side)) {
			movement =
				(mouseMoveEvent.clientY - startY) * (props.side === "top" ? -1 : 1) * props.resizeSensitivity;
		} else {
			movement =
				(mouseMoveEvent.clientX - startX) * (props.side === "left" ? -1 : 1) * props.resizeSensitivity;
		}

		let newDimension = startDimension + movement;
		// clamp width between min and max
		newDimension = Math.min(Math.max(props.minDimension, newDimension), props.maxDimension);
		emit("resize", newDimension);
		dragActive.value = true;
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			dragActive.value = false;
			mouseUpEvent.preventDefault();
		},
		{ once: true },
	);
}
</script>
