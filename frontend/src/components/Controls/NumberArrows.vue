<template>
	<div
		v-if="modelValue"
		class="pointer-events-none hidden flex-col gap-0 transition-opacity group-hover:pointer-events-auto group-hover:flex">
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
import { useIntervalFn, useTimeoutFn } from "@vueuse/core";

defineProps<{
	modelValue: boolean;
}>();

const emit = defineEmits(["increment", "decrement"]);

let heldDirection: "increment" | "decrement" | null = null;

// Repeats the emit while the button stays held; both timers auto-stop on unmount.
const { pause: stopRepeat, resume: startRepeat } = useIntervalFn(
	() => {
		if (heldDirection) emit(heldDirection);
	},
	50,
	{ immediate: false },
);

// Delay before the hold-to-repeat kicks in.
const { start: startDelay, stop: stopDelay } = useTimeoutFn(() => startRepeat(), 400, { immediate: false });

function startHold(direction: "increment" | "decrement") {
	heldDirection = direction;
	emit(direction);
	startDelay();
}

function stopHold() {
	stopDelay();
	stopRepeat();
	heldDirection = null;
}
</script>

<style scoped>
.circle-cursor {
	cursor:
		url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14'%3E%3Ccircle cx='7' cy='7' r='6' fill='gray' fill-opacity='0.4' stroke='none'/%3E%3C/svg%3E")
			7 7,
		auto;
}
</style>
