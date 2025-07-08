<template>
	<div class="flex items-center gap-2">
		<InputLabel v-if="label">{{ label }}</InputLabel>
		<BuilderInput
			:modelValue="modelValue"
			:hideClearButton="true"
			type="number"
			:min="min"
			:max="max"
			:step="step"
			@focus="$emit('focus')"
			@blur="$emit('blur')"
			@input="$emit('update:modelValue', $event)"></BuilderInput>
		<input
			type="range"
			:max="max"
			:min="min"
			:step="step"
			:value="modelValue"
			:placeholder="placeholder"
			@focus="$emit('focus')"
			@blur="$emit('blur')"
			@input="(ev: Event) => $emit('update:modelValue', (ev.target as HTMLInputElement).value)"
			ref="inputRef"
			class="range-input" />
	</div>
</template>
<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { nextTick, onMounted, ref, watch } from "vue";
const props = defineProps<{
	modelValue?: number | string;
	label?: string;
	min?: number;
	max?: number;
	step?: number;
	placeholder?: string;
}>();
const emit = defineEmits(["update:modelValue", "focus", "blur"]);
const inputRef = ref<HTMLInputElement | null>(null);
async function updatePercent() {
	await nextTick();
	if (!inputRef.value) return;
	const min = Number(props.min ?? 0);
	const max = Number(props.max ?? 100);
	const val = Number(props.modelValue ?? min);
	const percent = ((val - min) / (max - min)) * 100;
	inputRef.value.style.setProperty("--percent", percent + "%");
}
onMounted(updatePercent);
watch(() => props.modelValue, updatePercent);
</script>
<style scoped>
.range-input {
	@apply h-0.5 w-full cursor-pointer appearance-none rounded-full border-none bg-transparent;
	--percent: 0%;
}
/* Webkit (Chrome, Safari, Edge) */
.range-input::-webkit-slider-runnable-track {
	@apply h-0.5 rounded-full;
	background: linear-gradient(
		to right,
		var(--surface-gray-7) 0%,
		var(--surface-gray-7) calc(var(--percent, 0%) + 0.1%),
		var(--surface-gray-4) calc(var(--percent, 0%) + 0.1%),
		var(--surface-gray-4) 100%
	);
}

.range-input::-webkit-slider-thumb {
	@apply h-[14px] w-[14px] appearance-none rounded-full border-none bg-surface-gray-7 shadow-md;
	@apply -mt-[6px];
	transition: box-shadow 0.2s;
}
.range-input:active::-webkit-slider-thumb {
	@apply shadow-lg;
	@apply bg-surface-gray-4;
}
.range-input::-webkit-slider-thumb {
	border: none;
}

/* Firefox */
.range-input::-moz-range-track {
	@apply h-0.5 rounded-full bg-surface-gray-2;
}
.range-input::-moz-range-progress {
	@apply h-0.5 rounded-full bg-surface-gray-7;
}
.range-input::-moz-range-thumb {
	@apply h-[14px] w-[14px] rounded-full border-none bg-surface-gray-7 shadow-sm;
	transition: box-shadow 0.2s;
}
.range-input:active::-moz-range-thumb {
	@apply shadow-lg;
	@apply bg-surface-gray-4;
}

/* IE/Edge */
.range-input::-ms-fill-lower {
	@apply rounded-full bg-surface-gray-7;
}
.range-input::-ms-fill-upper {
	@apply rounded-full bg-surface-gray-2;
}
.range-input::-ms-thumb {
	@apply h-[14px] w-[14px] rounded-full border-none bg-surface-gray-7 shadow-sm;
	transition: box-shadow 0.2s;
}
.range-input:active::-ms-thumb {
	@apply shadow-lg;
	@apply bg-surface-gray-4;
}
.range-input:focus {
	@apply outline-none;
}

/* Hide outline for all browsers */
.range-input::-webkit-slider-thumb:focus {
	@apply outline-none;
}
.range-input::-moz-focus-outer {
	@apply border-0;
}
</style>
