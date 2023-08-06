<template>
	<InlineInput
		type="autocomplete"
		:options="[
			{
				label: 'Auto',
				value: 'auto',
			},
			{
				label: 'Fit Content',
				value: 'fit-content',
			},
		]"
		:modelValue="blockController.getStyle(property)"
		@update:modelValue="(val: string) => blockController.setStyle(property, val)">
		<slot />
	</InlineInput>
</template>
<script setup lang="ts">
import { styleProperty } from "@/utils/block";
import blockController from "@/utils/blockController";
import { PropType } from "vue";
import InlineInput from "./InlineInput.vue";

defineProps({
	property: {
		type: String as PropType<styleProperty>,
		required: true,
	},
});
</script>
