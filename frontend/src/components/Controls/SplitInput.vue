<template>
	<div class="w-full">
		<div class="flex divide-x divide-outline-gray-2 overflow-hidden rounded">
			<Input
				v-for="(split, index) in splits"
				:key="`input-${index}`"
				class="split-input min-w-0 flex-1 *:rounded-none *:p-2 *:text-xs *:text-center"
				:class="{
					'*:rounded-l': index == 0,
					'*:rounded-r': index == splits.length - 1,
				}"
				:modelValue="values[index]"
				:aria-label="split.label"
				:type="type"
				:hideClearButton="true"
				v-bind="getInputAttrs(index)"
				@keydown="(event: KeyboardEvent) => handleKeyDown(event, index)"
				@update:modelValue="(value) => updateValue(index, value)" />
		</div>

		<div v-if="hasLabels" class="mt-1 grid" :style="gridStyle">
			<span
				v-for="(split, index) in splits"
				:key="`label-${index}`"
				class="truncate text-center text-[8px] text-ink-gray-5"
				:class="{ 'cursor-ns-resize': enableSlider && split.label }"
				:title="split.label"
				@mousedown="handleLabelMouseDown($event, index)">
				{{ split.label }}
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
type Split = { label?: string; attrs?: InputAttrs };

const props = withDefaults(
	defineProps<{
		modelValue?: InputValue;
		// A count renders unlabelled splits; labels double as the slider handles.
		splits: number | (string | Split)[];
		toControlValues?: (value: unknown, count: number) => InputValue[];
		toModelValue?: (values: InputValue[], changedIndex: number) => unknown;
		normalizeValue?: (value: InputValue, index: number) => InputValue;
		inputAttrs?: InputAttrs;
		enableSlider?: boolean;
		type?: string;
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

const splits = computed<Split[]>(() =>
	typeof props.splits === "number"
		? Array.from({ length: props.splits }, () => ({}))
		: props.splits.map((split) => (typeof split === "string" ? { label: split } : split)),
);

const hasLabels = computed(() => splits.value.some((split) => split.label));

const values = computed(() => {
	const splitValues = props.toControlValues(props.modelValue, splits.value.length);
	return Array.from({ length: splits.value.length }, (_, index) => splitValues[index] ?? "");
});

const gridStyle = computed(() => ({
	gridTemplateColumns: `repeat(${splits.value.length}, minmax(0, 1fr))`,
}));

const getInputAttrs = (index: number) => ({ ...props.inputAttrs, ...splits.value[index]?.attrs });

const updateValue = (index: number, value: InputValue) => {
	// Every side is normalized, not just the edited one, so units stay consistent across sides.
	const nextValues = values.value.map((current, side) =>
		props.normalizeValue(side === index ? value : current, side),
	);
	emit("update:modelValue", props.toModelValue(nextValues, index));
};

const getNumericBounds = (index: number) => {
	const attrs = getInputAttrs(index);
	return {
		step: Number(attrs.step) || 1,
		min: attrs.min === undefined ? -Infinity : Number(attrs.min),
		max: attrs.max === undefined ? Infinity : Number(attrs.max),
	};
};

const setNumericValue = (index: number, value: number, unit: string, min: number, max: number) => {
	updateValue(index, `${Math.max(min, Math.min(max, value))}${unit}`);
};

// TODO: Duplicating code over BasePropertyControl, refactor
const handleKeyDown = (event: KeyboardEvent, index: number) => {
	if (!props.enableSlider || (event.key !== "ArrowUp" && event.key !== "ArrowDown")) return;
	event.preventDefault();

	const { number, unit } = extractNumberAndUnit(String(values.value[index] ?? ""));
	const { step, min, max } = getNumericBounds(index);
	const direction = event.key === "ArrowUp" ? 1 : -1;
	setNumericValue(index, Number(number) + direction * step, unit, min, max);
};

const handleLabelMouseDown = (event: MouseEvent, index: number) => {
	if (!props.enableSlider || !splits.value[index]?.label) return;
	event.preventDefault();

	const { number, unit } = extractNumberAndUnit(String(values.value[index] ?? ""));
	const startValue = Number(number);
	const startY = event.clientY;
	const { step, min, max } = getNumericBounds(index);

	startDrag({
		cursor: window.getComputedStyle(event.currentTarget as HTMLElement).cursor,
		onMove: (moveEvent) => {
			const difference = Math.round(startY - moveEvent.clientY) * step;
			setNumericValue(index, startValue + difference, unit, min, max);
		},
	});
};
</script>
