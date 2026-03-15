<template>
	<div
		class="shadow-inner relative size-6 flex-shrink-0 cursor-pointer rounded-full border border-outline-gray-2 bg-surface-gray-2 transition-all hover:border-outline-gray-3"
		ref="dialRef"
		@mousedown="handleMouseDown">
		<!-- Degrees indicator -->
		<div
			class="absolute left-1/2 top-1/2 h-1/2 w-0.5 origin-top -translate-x-1/2 bg-surface-gray-7 pt-1"
			:style="{ transform: `translateX(-50%) rotate(${modelValue + 180}deg)` }">
			<div
				class="absolute -bottom-1 left-1/2 size-2 -translate-x-1/2 rounded-full border border-outline-gray-3 bg-surface-gray-7 shadow-sm" />
		</div>
		<!-- Center point -->
		<div
			class="bg-outline-gray-3 absolute left-1/2 top-1/2 size-1 -translate-x-1/2 -translate-y-1/2 rounded-full" />
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
	modelValue: number;
}>();

const emit = defineEmits(["update:modelValue"]);

const dialRef = ref<HTMLElement | null>(null);

const handleMouseDown = (e: MouseEvent) => {
	updateAngle(e);
	document.body.style.userSelect = "none";
	window.addEventListener("mousemove", updateAngle);
	window.addEventListener(
		"mouseup",
		() => {
			window.removeEventListener("mousemove", updateAngle);
			document.body.style.userSelect = "";
		},
		{ once: true },
	);
};

const updateAngle = (e: MouseEvent) => {
	if (!dialRef.value) return;
	const rect = dialRef.value.getBoundingClientRect();
	const centerX = rect.left + rect.width / 2;
	const centerY = rect.top + rect.height / 2;

	const dx = e.clientX - centerX;
	const dy = e.clientY - centerY;

	// atan2 returns radians between -PI and PI
	// We add 90 degrees (Math.PI / 2) because CSS 0deg is top (straight up)
	let angle = Math.atan2(dy, dx) * (180 / Math.PI) + 90;

	// Normalize to 0-360
	angle = (angle + 360) % 360;

	emit("update:modelValue", Math.round(angle));
};
</script>
