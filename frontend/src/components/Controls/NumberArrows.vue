<template>
	<div
		v-if="modelValue"
		class="pointer-events-none flex flex-col gap-0 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100">
		<button
			type="button"
			class="circle-cursor duration-250 -mb-[1.5px] flex h-3 w-5 items-center justify-center rounded text-ink-gray-5 transition-all ease-in-out active:-translate-y-[2px] active:text-ink-gray-9"
			@mousedown.prevent.stop="startHold('increment')"
			@mouseup="stopHold"
			@mouseleave="stopHold"
			tabindex="-1">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="12"
				height="12"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round">
				<polyline points="18 15 12 9 6 15"></polyline>
			</svg>
		</button>
		<button
			type="button"
			class="circle-cursor duration-250 -mt-[1.5px] flex h-3 w-5 items-center justify-center rounded text-ink-gray-5 transition-all ease-in-out active:translate-y-[2px] active:text-ink-gray-9"
			@mousedown.prevent.stop="startHold('decrement')"
			@mouseup="stopHold"
			@mouseleave="stopHold"
			tabindex="-1">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="12"
				height="12"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round">
				<polyline points="6 9 12 15 18 9"></polyline>
			</svg>
		</button>
	</div>
</template>

<script lang="ts" setup>
defineProps<{
	modelValue: boolean;
}>();

const emit = defineEmits(["increment", "decrement"]);

let holdTimeout: ReturnType<typeof setTimeout> | null = null;
let holdInterval: ReturnType<typeof setInterval> | null = null;

function startHold(direction: "increment" | "decrement") {
	emit(direction);
	holdTimeout = setTimeout(() => {
		holdInterval = setInterval(() => {
			emit(direction);
		}, 50);
	}, 400);
}

function stopHold() {
	if (holdTimeout) {
		clearTimeout(holdTimeout);
		holdTimeout = null;
	}
	if (holdInterval) {
		clearInterval(holdInterval);
		holdInterval = null;
	}
}
</script>

<style scoped>
.circle-cursor {
	cursor:
		url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14'%3E%3Ccircle cx='7' cy='7' r='6' fill='gray' fill-opacity='0.2' stroke='none'/%3E%3C/svg%3E")
			7 7,
		auto;
}
</style>
