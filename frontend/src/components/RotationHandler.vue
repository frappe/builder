<template>
	<div
		v-for="corner in corners"
		:key="corner.name"
		class="pointer-events-auto absolute size-7 rounded-full"
		:class="corner.positionClass"
		:style="{ cursor: corner.cursor.value }"
		@mousedown.stop.prevent="(ev) => handleRotate(ev, corner.baseAngle)" />
</template>

<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import rotationCursorSvg from "@/assets/rotation-cursor.svg?raw";
import { clearDragCursor, getRotatedCursor, setDragCursor } from "@/utils/cursor";
import { getElementRotation, getTotalRotation } from "@/utils/rotation";
import { computed } from "vue";

const props = defineProps<{
	targetBlock: Block;
	target: HTMLElement | SVGElement;
}>();

const emit = defineEmits<{
	rotating: [value: boolean];
}>();

const canvasStore = useCanvasStore();

const cornerLayout = [
	{ name: "bottom-right", positionClass: "bottom-[-20px] right-[-20px]", baseAngle: 0 },
	{ name: "bottom-left", positionClass: "bottom-[-20px] left-[-20px]", baseAngle: 90 },
	{ name: "top-left", positionClass: "top-[-20px] left-[-20px]", baseAngle: 180 },
	{ name: "top-right", positionClass: "top-[-20px] right-[-20px]", baseAngle: 270 },
] as const;

const corners = cornerLayout.map((corner) => ({
	...corner,
	cursor: computed(() =>
		getRotatedCursor(
			rotationCursorSvg,
			getTotalRotation(props.target as Element, props.targetBlock) + corner.baseAngle,
			"pointer",
		),
	),
}));

const handleRotate = (ev: MouseEvent, baseAngle: number) => {
	const bounds = props.target.getBoundingClientRect();
	const centerX = bounds.left + bounds.width / 2;
	const centerY = bounds.top + bounds.height / 2;
	let previousPointerAngle = Math.atan2(ev.clientY - centerY, ev.clientX - centerX) * (180 / Math.PI);
	let rotation = parseFloat(String(props.targetBlock.getStyle("rotate") || 0)) || 0;
	// ancestors don't rotate mid-drag, so their contribution can be captured once up front
	const ancestorRotation = getElementRotation((props.target as Element).parentElement);
	const pauseId = canvasStore.activeCanvas?.history?.pause();
	let lastCursorAngle: number | null = null;
	setDragCursor(getRotatedCursor(rotationCursorSvg, ancestorRotation + rotation + baseAngle, "pointer"));
	emit("rotating", true);

	const mousemove = (mouseMoveEvent: MouseEvent) => {
		const pointerAngle =
			Math.atan2(mouseMoveEvent.clientY - centerY, mouseMoveEvent.clientX - centerX) * (180 / Math.PI);
		let angleChange = pointerAngle - previousPointerAngle;
		if (angleChange > 180) angleChange -= 360;
		if (angleChange < -180) angleChange += 360;
		rotation = (rotation + angleChange) % 360;
		previousPointerAngle = pointerAngle;
		const finalRotation = mouseMoveEvent.shiftKey ? Math.round(rotation / 15) * 15 : Math.round(rotation);
		props.targetBlock.setStyle("rotate", `${finalRotation}deg`);
		// the cursor SVG only needs rebuilding when the rounded/snapped angle actually
		// changes - most mousemove ticks land on the same value, especially while snapping
		if (finalRotation !== lastCursorAngle) {
			lastCursorAngle = finalRotation;
			setDragCursor(
				getRotatedCursor(rotationCursorSvg, ancestorRotation + finalRotation + baseAngle, "pointer"),
			);
		}
		mouseMoveEvent.preventDefault();
	};

	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			clearDragCursor();
			document.removeEventListener("mousemove", mousemove);
			emit("rotating", false);
			mouseUpEvent.preventDefault();
			canvasStore.activeCanvas?.history?.resume(pauseId, true);
		},
		{ once: true },
	);
};
</script>
