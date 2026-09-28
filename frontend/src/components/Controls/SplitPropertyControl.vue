<template>
	<StylePropertyControl v-bind="{ ...splitProps, ...$attrs }" :component="SplitModeInput">
		<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
			<slot :name="name" v-bind="slotData || {}" />
		</template>
	</StylePropertyControl>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import { collapseBoxShorthand, expandBoxShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { BOX_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed } from "vue";

defineOptions({ inheritAttrs: false });

type InputAttrs = Record<string, unknown>;
type SplitConfig = string | { label?: string; attrs?: InputAttrs };

const props = withDefaults(
	defineProps<{
		propertyKey: string;
		splits: number | SplitConfig[];
		unitOptions?: string[];
		toControlValues?: (value: unknown, count: number) => StyleValue[];
		toModelValue?: (values: StyleValue[], changedIndex: number) => unknown;
		normalizeValue?: (value: StyleValue, index: number) => StyleValue;
		inputAttrs?: InputAttrs;
		// Reads the base value when called without a state, the variant value otherwise.
		getModelValue?: (state?: string | null) => string | number | boolean;
		getVariantValue?: (variant: string) => string | number | boolean;
	}>(),
	{
		unitOptions: () => BOX_UNIT_OPTIONS,
		toControlValues: (value: unknown) => expandBoxShorthand(value),
		toModelValue: (values: StyleValue[]) => collapseBoxShorthand(values),
		inputAttrs: () => ({ min: 0 }),
	},
);

const defaultUnit = computed(() => props.unitOptions[0] ?? "px");

const normalizeValue = computed(
	() =>
		props.normalizeValue ??
		((value: StyleValue) => normalizeValueWithUnits(String(value || "0"), defaultUnit.value)),
);

const splitProps = computed(() => ({
	...props,
	enableSlider: true,
	normalizeValue: normalizeValue.value,
	getVariantValue: props.getVariantValue ?? props.getModelValue,
}));
</script>
