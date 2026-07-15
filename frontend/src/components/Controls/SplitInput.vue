<template>
	<div class="w-full">
		<div class="flex overflow-hidden rounded">
			<Input
				v-for="(label, index) in labels"
				:key="`input-${index}`"
				class="split-input min-w-0 flex-1 *:rounded-none *:p-2 *:text-xs *:text-center"
				:class="{
					'border-l border-outline-gray-2': index > 0,
					'*:rounded-l': index == 0,
					'*:rounded-r': index == labels.length - 1,
				}"
				:modelValue="values[index]"
				:aria-label="label"
				:hideClearButton="true"
				v-bind="getInputAttrs(index)"
				@update:modelValue="(value) => updateValue(index, value)" />
		</div>

		<div class="mt-1 grid" :style="gridStyle">
			<span
				v-for="(label, index) in labels"
				:key="`label-${label}`"
				class="cursor-ns-resize truncate text-center text-[8px] text-ink-gray-5"
				:title="label"
				@mousedown.prevent="handleLabelMouseDown($event, index)">
				{{ label }}
			</span>
		</div>
	</div>
</template>

<script lang="ts" setup>
import Input from "@/components/Controls/Input.vue";
import { extractNumberAndUnit } from "@/utils/helpers";
import { computed } from "vue";

type InputValue = string | number | boolean | null;
type InputAttrs = Record<string, unknown>;

const props = withDefaults(
	defineProps<{
		modelValue?: unknown;
		labels: string[];
		splitValue?: (value: unknown, count: number) => InputValue[];
		combineValues?: (values: InputValue[], changedIndex: number) => unknown;
		normalizeValue?: (value: InputValue, index: number) => InputValue;
		inputAttrs?: InputAttrs | ((index: number) => InputAttrs);
	}>(),
	{
		splitValue: (value: unknown) => (Array.isArray(value) ? value : [value as InputValue]),
		combineValues: (values: InputValue[]) => values,
		normalizeValue: (value: InputValue) => value,
		inputAttrs: () => ({}),
	},
);

const emit = defineEmits<{
	"update:modelValue": [value: unknown];
}>();

const values = computed(() => {
	const splitValues = props.splitValue(props.modelValue, props.labels.length);
	return Array.from({ length: props.labels.length }, (_, index) => splitValues[index] ?? "");
});

const gridStyle = computed(() => ({
	gridTemplateColumns: `repeat(${props.labels.length}, minmax(0, 1fr))`,
}));

const getInputAttrs = (index: number) =>
	typeof props.inputAttrs === "function" ? props.inputAttrs(index) : props.inputAttrs;

const updateValue = (index: number, value: InputValue) => {
	const nextValues: InputValue[] = [...values.value];
	nextValues[index] = props.normalizeValue(value, index);
	emit("update:modelValue", props.combineValues(nextValues, index));
};

const handleLabelMouseDown = (event: MouseEvent, index: number) => {
	const { number, unit } = extractNumberAndUnit(String(values.value[index] ?? ""));
	const startValue = Number(number);
	const startY = event.clientY;
	const attrs = getInputAttrs(index);
	const step = Number(attrs.step) || 1;
	const min = attrs.min === undefined ? -Infinity : Number(attrs.min);
	const max = attrs.max === undefined ? Infinity : Number(attrs.max);

	const handleMouseMove = (event: MouseEvent) => {
		const difference = Math.round(startY - event.clientY) * step;
		const nextValue = Math.max(min, Math.min(max, startValue + difference));
		updateValue(index, `${nextValue}${unit}`);
	};

	const handleMouseUp = () => window.removeEventListener("mousemove", handleMouseMove);
	window.addEventListener("mousemove", handleMouseMove);
	window.addEventListener("mouseup", handleMouseUp, { once: true });
};
</script>
