<template>
	<div class="flex w-full items-center gap-2 overflow-hidden">
		<InputLabel class="w-[80px] shrink-0 truncate">{{ label }}</InputLabel>
		<BuilderInput
			:type="type"
			:modelValue="modelValue"
			:placeholder="placeholderValue"
			@update:modelValue="updateValue"
			:options="options"
			class="w-full"></BuilderInput>
	</div>
</template>
<script lang="ts" setup>
import InputLabel from "@/components/Controls/InputLabel.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const props = withDefaults(
	defineProps<{
		styleProperty: string;
		label?: string;
		placeholder?: string;
		options?: Record<string, string>;
		getModelValue?: () => string;
		getPlaceholder?: () => string;
		setModelValue?: (value: string) => void;
		type?: string;
	}>(),
	{
		label: "",
		placeholder: "unset",
		type: "text",
	},
);

const modelValue = computed(
	() => props.getModelValue?.() ?? blockController.getNativeStyle(props.styleProperty) ?? "",
);

const placeholderValue = computed(
	() =>
		props.getPlaceholder?.() ??
		String(blockController.getCascadingStyle(props.styleProperty) ?? props.placeholder),
);

const updateValue = (value: string) => {
	if (props.setModelValue) {
		props.setModelValue(value);
	} else {
		blockController.setStyle(props.styleProperty, value);
	}
};
</script>
