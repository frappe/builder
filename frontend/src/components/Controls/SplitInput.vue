<template>
	<div class="w-full">
		<div class="flex divide-x divide-outline-gray-2 overflow-hidden rounded">
			<Input
				v-for="(label, index) in labels"
				:key="`input-${index}`"
				class="split-input min-w-0 flex-1 *:rounded-none *:p-2 *:text-xs *:text-center"
				:class="{
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
				class="truncate text-center text-[8px] text-ink-gray-5"
				:class="{ 'cursor-ns-resize': enableSlider }"
				:title="label"
				@mousedown="handleLabelMouseDown($event, index)">
				{{ label }}
			</span>
		</div>
	</div>
</template>

<script lang="ts" setup>
import Input from "@/components/Controls/Input.vue";
import { startDrag } from "@/utils/cursor";
import { extractNumberAndUnit } from "@/utils/helpers";
import { computed } from "vue";

type InputValue = string | number | boolean | null;
type InputAttrs = Record<string, unknown>;

const props = withDefaults(
	defineProps<{
		modelValue?: unknown;
		labels: string[];
		toControlValues?: (value: unknown, count: number) => InputValue[];
		toModelValue?: (values: InputValue[], changedIndex: number) => unknown;
		normalizeValue?: (value: InputValue, index: number) => InputValue;
		inputAttrs?: InputAttrs | ((index: number) => InputAttrs);
		enableSlider?: boolean;
	}>(),
	{
		toControlValues: (value: unknown) => (Array.isArray(value) ? value : [value as InputValue]),
		toModelValue: (values: InputValue[]) => values,
		normalizeValue: (value: InputValue) => value,
		inputAttrs: () => ({}),
		enableSlider: false,
	},
);

const emit = defineEmits<{
	"update:modelValue": [value: unknown];
}>();

const values = computed(() => {
	const splitValues = props.toControlValues(props.modelValue, props.labels.length);
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
	emit("update:modelValue", props.toModelValue(nextValues, index));
};

const handleLabelMouseDown = (event: MouseEvent, index: number) => {
	if (!props.enableSlider) return;
	event.preventDefault();

	const { number, unit } = extractNumberAndUnit(String(values.value[index] ?? ""));
	const startValue = Number(number);
	const startY = event.clientY;
	const attrs = getInputAttrs(index);
	const step = Number(attrs.step) || 1;
	const min = attrs.min === undefined ? -Infinity : Number(attrs.min);
	const max = attrs.max === undefined ? Infinity : Number(attrs.max);

	startDrag({
		cursor: window.getComputedStyle(event.currentTarget as HTMLElement).cursor,
		onMove: (moveEvent) => {
			const difference = Math.round(startY - moveEvent.clientY) * step;
			const nextValue = Math.max(min, Math.min(max, startValue + difference));
			updateValue(index, `${nextValue}${unit}`);
		},
	});
};
</script>
