<template>
	<InlineInput
		type="autocomplete"
		:label="label"
		:enableSlider="true"
		:options="[
			{
				label: 'Auto',
				value: 'auto',
			},
			{
				label: 'Fit Content',
				value: 'fit-content',
			},
			{
				label: 'Stretch',
				value: '100%',
			},
		]"
		:modelValue="blockController.getStyle(props.property) || 'auto'"
		:unitOptions="['px', '%', 'vw', 'vh']"
		@update:modelValue="(val) => blockController.setStyle(property, val)"></InlineInput>
</template>
<script setup lang="ts">
import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";

const props = defineProps<{
	property: styleProperty;
	label: string;
}>();
</script>
