<template>
	<InlineInput
		type="autocomplete"
		:label="label"
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
		:modelValue="blockController.getStyle(props.property)"
		@update:modelValue="(val) => blockController.setStyle(property, val)"></InlineInput>
</template>
<script setup lang="ts">
import { styleProperty } from "@/utils/block";
import blockController from "@/utils/blockController";
import { PropType } from "vue";
import InlineInput from "./InlineInput.vue";

const props = defineProps({
	property: {
		type: String as PropType<styleProperty>,
		required: true,
	},
	label: {
		type: String,
		required: true,
	},
});
</script>
