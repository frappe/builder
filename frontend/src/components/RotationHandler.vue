<template>
	<div
		class="rotation-cursor pointer-events-auto absolute bottom-[-20px] right-[-20px] size-7 rounded-full"
		@mousedown.stop.prevent="handleRotate" />
</template>

<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";

const props = defineProps<{
	targetBlock: Block;
	target: HTMLElement | SVGElement;
}>();

const emit = defineEmits<{
	rotating: [value: boolean];
}>();

const canvasStore = useCanvasStore();

const handleRotate = (ev: MouseEvent) => {
	const bounds = props.target.getBoundingClientRect();
	const centerX = bounds.left + bounds.width / 2;
	const centerY = bounds.top + bounds.height / 2;
	let previousPointerAngle = Math.atan2(ev.clientY - centerY, ev.clientX - centerX) * (180 / Math.PI);
	let rotation = parseFloat(String(props.targetBlock.getStyle("rotate") || 0)) || 0;
	const pauseId = canvasStore.activeCanvas?.history?.pause();
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.currentTarget as HTMLElement).cursor;
	emit("rotating", true);

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		const pointerAngle =
			Math.atan2(mouseMoveEvent.clientY - centerY, mouseMoveEvent.clientX - centerX) * (180 / Math.PI);
		let angleChange = pointerAngle - previousPointerAngle;
		if (angleChange > 180) angleChange -= 360;
		if (angleChange < -180) angleChange += 360;
		rotation += angleChange;
		previousPointerAngle = pointerAngle;
		const finalRotation = mouseMoveEvent.shiftKey ? Math.round(rotation / 15) * 15 : Math.round(rotation);
		props.targetBlock.setStyle("rotate", `${finalRotation}deg`);
		mouseMoveEvent.preventDefault();
	};

	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			emit("rotating", false);
			mouseUpEvent.preventDefault();
			canvasStore.activeCanvas?.history?.resume(pauseId, true);
		},
		{ once: true },
	);
};
</script>

<style scoped>
.rotation-cursor {
	cursor: url("@/assets/rotation-cursor.svg") 16 16, pointer;
}
</style>
