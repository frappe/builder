<template>
	<div
		class="shadow-inner relative size-6 flex-shrink-0 cursor-pointer rounded-full border border-outline-gray-2 bg-surface-gray-2 transition-all hover:border-outline-gray-3"
		ref="dialRef">
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
import { useMouseInElement, useMousePressed } from "@vueuse/core";
import { ref, watch } from "vue";

const props = defineProps<{
	modelValue: number;
}>();

const emit = defineEmits(["update:modelValue"]);

const dialRef = ref<HTMLElement | null>(null);
const { elementX, elementY, elementWidth, elementHeight } = useMouseInElement(dialRef);
const { pressed } = useMousePressed();

watch([elementX, elementY, pressed], () => {
	if (!pressed.value) return;

	const dx = elementX.value - elementWidth.value / 2;
	const dy = elementY.value - elementHeight.value / 2;

	let angle = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
	angle = (angle + 360) % 360;

	emit("update:modelValue", Math.round(angle));
});
</script>
