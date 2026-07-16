<template>
	<div class="flex w-full min-w-0 flex-col gap-2" v-bind="rootAttrs">
		<div class="flex w-full min-w-0 gap-2">
			<Input
				class="min-w-0 flex-1"
				:modelValue="displayValue"
				:placeholder="split && labels.length && !displayValue ? 'Mixed' : placeholder"
				v-bind="controlAttrs"
				@update:modelValue="setUniformValue" />

			<TabButtons
				class="shrink-0"
				:modelValue="split"
				:options="resolvedSplitOptions"
				@update:modelValue="setSplitValue" />
		</div>

		<SplitInput
			v-if="split && labels.length"
			:modelValue="modelValue"
			:labels="labels"
			:splitValue="splitValue"
			:combineValues="combineValues"
			:normalizeValue="normalizeValue"
			:inputAttrs="inputAttrs"
			:enableSlider="enableSlider"
			@update:modelValue="setIndividualValue" />
	</div>
</template>

<script lang="ts" setup>
import Input from "@/components/Controls/Input.vue";
import SplitInput from "@/components/Controls/SplitInput.vue";
import { expandBoxShorthand } from "@/utils/cssUtils";
import { TabButtons, type TabButton } from "frappe-ui";
import type { Component, HTMLAttributes } from "vue";
import { computed, useAttrs } from "vue";

defineOptions({ inheritAttrs: false });

type InputValue = string | number | boolean | null;
type InputAttrs = Record<string, unknown>;
type SplitOption = Omit<TabButton, "value"> & { value: boolean };

const props = withDefaults(
	defineProps<{
		modelValue?: InputValue;
		placeholder?: string | number | boolean;
		split?: boolean;
		uniformTitle?: string;
		splitTitle?: string;
		splitOptions?: SplitOption[];
		labels?: string[];
		splitValue?: (value: unknown, count: number) => InputValue[];
		combineValues?: (values: InputValue[], changedIndex: number) => unknown;
		normalizeValue?: (value: InputValue, index: number) => InputValue;
		inputAttrs?: InputAttrs | ((index: number) => InputAttrs);
		enableSlider?: boolean;
		getMergedValue: (values: InputValue[]) => InputValue;
	}>(),
	{
		modelValue: "",
		placeholder: "",
		split: false,
		uniformTitle: "Use uniform value",
		splitTitle: "Use individual values",
		labels: () => [],
		splitValue: (value: unknown) => (Array.isArray(value) ? value : [value as InputValue]),
		combineValues: (values: InputValue[]) => values,
		normalizeValue: (value: InputValue) => value,
		inputAttrs: () => ({}),
		enableSlider: false,
	},
);

const emit = defineEmits<{
	"update:modelValue": [value: InputValue];
	"update:split": [value: boolean];
}>();

const attrs = useAttrs();
const rootAttrs = computed(() => ({ class: attrs.class, style: attrs.style } as HTMLAttributes));
const controlAttrs = computed(() =>
	Object.fromEntries(Object.entries(attrs).filter(([key]) => !["class", "style"].includes(key))),
);

const splitValues = computed(() => props.splitValue(props.modelValue, props.labels.length));
const displayValue = computed(() => {
	if (!props.split) return props.modelValue;
	if (String(props.modelValue ?? "").trim() === "Mixed") return "";
	const values = expandBoxShorthand(props.modelValue);
	return new Set(values).size === 1 ? values[0] : "";
});

const defaultSplitOptions = computed<SplitOption[]>(() => [
	{
		label: props.uniformTitle,
		value: false,
		icon: "lucide-square",
		tooltip: props.uniformTitle,
	},
	{
		label: props.splitTitle,
		value: true,
		icon: "lucide-scan",
		tooltip: props.splitTitle,
	},
]);

const resolvedSplitOptions = computed(() => props.splitOptions ?? defaultSplitOptions.value);

const setSplitValue = (value: string | number | boolean | undefined) => {
	if (typeof value !== "boolean") return;
	if (!value) {
		const mergedValue = props.getMergedValue(splitValues.value);
		setUniformValue(mergedValue);
		return;
	}
	emit("update:split", value);
};

const setIndividualValue = (value: unknown) => emit("update:modelValue", value as InputValue);

const setUniformValue = (value: InputValue) => {
	if (String(value ?? "") === String(displayValue.value ?? "")) return;
	if (props.split) emit("update:split", false);
	emit("update:modelValue", value);
};
</script>
