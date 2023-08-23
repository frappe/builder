<template>
	<div
		class="absolute bottom-0 top-0 w-1 bg-transparent hover:cursor-ew-resize"
		:class="{
			'left-0': side === 'left',
			'right-0': side === 'right',
			'bg-gray-300 dark:bg-zinc-700': dragActive,
		}"
		@mousedown="resize">
		<slot />
	</div>
</template>
<script setup lang="ts">
import { ref } from "vue";
const props = defineProps({
	maxWidth: {
		type: Number,
		default: 350,
	},
	minWidth: {
		type: Number,
		default: 280,
	},
	width: {
		type: Number,
		default: 300,
	},
	side: {
		type: String,
		default: "right",
	},
	resizeSensitivity: {
		type: Number,
		default: 1,
	},
});

const emit = defineEmits({
	resize: (width) => width,
});

const dragActive = ref(false);

function resize(ev: MouseEvent) {
	const startX = ev.clientX;
	const startWidth = props.width;
	const target = ev.target as HTMLElement;
	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(target).cursor;

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		const movement =
			(mouseMoveEvent.clientX - startX) * (props.side === "left" ? -1 : 1) * props.resizeSensitivity;
		let newWidth = startWidth + movement;
		// clamp width between min and max
		newWidth = Math.min(Math.max(props.minWidth, newWidth), props.maxWidth);
		emit("resize", newWidth);
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
		{ once: true }
	);
}
</script>
