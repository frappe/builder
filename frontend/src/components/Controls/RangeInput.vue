<template>
	<div class="flex items-center gap-2">
		<InputLabel>{{ label }}</InputLabel>
		<BuilderInput
			:modelValue="modelValue"
			:hideClearButton="true"
			@update:modelValue="$emit('update:modelValue', $event)"></BuilderInput>
		<input
			type="range"
			:max="max"
			:min="min"
			:step="step"
			:value="modelValue"
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
}>();
const emit = defineEmits(["update:modelValue"]);
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
	height: 2px;
	width: 100%;
	appearance: none;
	background: transparent;
	border: none;
	cursor: pointer;
	border-radius: 9999px;
	--percent: 0%;
}
/* Webkit (Chrome, Safari, Edge) */
.range-input::-webkit-slider-runnable-track {
	height: 2px;
	background: linear-gradient(
		to right,
		#000 0%,
		#000 calc(var(--percent, 0%) + 0.1%),
		#b9b9b9 calc(var(--percent, 0%) + 0.1%),
		#bcbcbc 100%
	);
	border-radius: 9999px;
}
.range-input::-webkit-slider-thumb {
	appearance: none;
	height: 14px;
	width: 14px;
	border-radius: 50%;
	background: #000;
	margin-top: -6px;
	box-shadow: 0 0 0 1px #0001;
	border: none;
}
.range-input::-webkit-slider-thumb {
	border: none;
}

/* Firefox */
.range-input::-moz-range-track {
	height: 2px;
	background: #bcbcbc;
	border-radius: 9999px;
}
.range-input::-moz-range-progress {
	height: 2px;
	background: #000;
	border-radius: 9999px;
}
.range-input::-moz-range-thumb {
	height: 14px;
	width: 14px;
	border-radius: 50%;
	background: #000;
	border: none;
}

/* IE/Edge */
.range-input::-ms-fill-lower {
	background: #000;
	border-radius: 9999px;
}
.range-input::-ms-fill-upper {
	background: #bcbcbc;
	border-radius: 9999px;
}
.range-input::-ms-thumb {
	height: 14px;
	width: 14px;
	border-radius: 50%;
	background: #000;
	border: none;
}
.range-input:focus {
	outline: none;
}

/* Hide outline for all browsers */
.range-input::-webkit-slider-thumb:focus {
	outline: none;
}
.range-input::-moz-focus-outer {
	border: 0;
}
</style>
