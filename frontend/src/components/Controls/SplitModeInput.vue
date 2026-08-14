<template>
	<div class="flex w-full min-w-0 flex-col gap-2" v-bind="rootAttrs">
		<div class="flex w-full min-w-0 gap-2">
			<Input
				class="min-w-0 flex-1"
				:modelValue="displayValue"
				:placeholder="split && splitCount && !displayValue && modelValue ? 'Mixed' : placeholder"
				:type="type"
				v-bind="controlAttrs"
				@update:modelValue="setUniformValue" />

			<TabButtons
				class="shrink-0"
				:modelValue="split"
				:options="resolvedSplitOptions"
				@update:modelValue="setSplitValue" />
		</div>

		<SplitInput
			v-if="split && splitCount"
			:modelValue="modelValue"
			:splits="splits"
			:toControlValues
			:toModelValue
			:normalizeValue="normalizeValue"
			:inputAttrs="inputAttrs"
			:enableSlider="enableSlider"
			:type="type"
			@update:modelValue="setIndividualValue" />
	</div>
</template>

<script lang="ts" setup>
import Input from "@/components/Controls/Input.vue";
import SplitInput from "@/components/Controls/SplitInput.vue";
import { __ } from "@/translation";
import blockController from "@/utils/blockController";
import { expandBoxShorthand } from "@/utils/cssUtils";
import { TabButtons, type TabButton } from "frappe-ui";
import type { HTMLAttributes } from "vue";
import { computed, ref, useAttrs, watch } from "vue";

defineOptions({ inheritAttrs: false });

type InputValue = string | number | boolean | null;
type InputAttrs = Record<string, unknown>;
type SplitConfig = string | { label?: string; attrs?: InputAttrs };
type SplitOption = Omit<TabButton, "value"> & { value: boolean };

const props = withDefaults(
	defineProps<{
		modelValue?: InputValue;
		placeholder?: string | number | boolean;
		uniformTitle?: string;
		splitTitle?: string;
		splitIcon?: string;
		splitOptions?: SplitOption[];
		splits?: number | SplitConfig[];
		toControlValues?: (value: unknown, count: number) => InputValue[];
		toModelValue?: (values: InputValue[], changedIndex: number) => unknown;
		normalizeValue?: (value: InputValue, index: number) => InputValue;
		inputAttrs?: InputAttrs;
		enableSlider?: boolean;
		type?: string;
		getMergedValue?: (values: InputValue[]) => InputValue;
	}>(),
	{
		modelValue: "",
		placeholder: "",
		uniformTitle: __("Use for all"),
		splitTitle: __("Set separately"),
		splitIcon: "lucide-scan",
		splits: 0,
		toControlValues: (value: unknown) => (Array.isArray(value) ? value : [value as InputValue]),
		toModelValue: (values: InputValue[]) => values,
		normalizeValue: (value: InputValue) => value,
		inputAttrs: () => ({}),
		// The base control filters its own enableSlider out of the fallthrough attrs, so split
		// inputs opt in here instead.
		enableSlider: true,
		getMergedValue: (values: InputValue[]) => values[0] ?? "0px",
	},
);

const emit = defineEmits<{
	"update:modelValue": [value: InputValue];
}>();

const attrs = useAttrs();
const rootAttrs = computed(() => ({ class: attrs.class, style: attrs.style }) as HTMLAttributes);
const controlAttrs = computed(() =>
	Object.fromEntries(Object.entries(attrs).filter(([key]) => !["class", "style"].includes(key))),
);

const splitCount = computed(() => (typeof props.splits === "number" ? props.splits : props.splits.length));
const splitValues = computed(() => props.toControlValues(props.modelValue, splitCount.value));

// Split mode turns itself on when the sides already differ; the toggle only forces it on.
const forceSplit = ref(false);
const split = computed(() => new Set(splitValues.value).size > 1 || forceSplit.value);
watch(
	() => blockController.getSelectedBlocks(),
	() => (forceSplit.value = false),
);

const displayValue = computed(() => {
	if (!split.value) return props.modelValue;
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
		icon: props.splitIcon,
		tooltip: props.splitTitle,
	},
]);

const resolvedSplitOptions = computed(() => props.splitOptions ?? defaultSplitOptions.value);

const setSplitValue = (value: string | number | boolean | undefined) => {
	if (typeof value !== "boolean") return;
	if (!value) emit("update:modelValue", props.getMergedValue(splitValues.value));
	forceSplit.value = value;
};

const setIndividualValue = (value: unknown) => emit("update:modelValue", value as InputValue);

const setUniformValue = (value: InputValue) => {
	if (String(value ?? "") === String(displayValue.value ?? "")) return;
	forceSplit.value = false;
	emit("update:modelValue", value);
};
</script>
