<template>
	<StylePropertyControl
		:component="Autocomplete"
		:propertyKey="property"
		:label="label"
		:enableSlider="true"
		:options="[
			{
				label: __('Auto'),
				value: 'auto',
			},
			{
				label: __('Fit Content'),
				value: 'fit-content',
			},
			{
				label: __('Stretch'),
				value: '100%',
			},
		]"
		:unitOptions="DIMENSION_UNIT_OPTIONS"></StylePropertyControl>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import { DIMENSION_UNIT_OPTIONS } from "@/utils/unitOptions";

defineProps<{
	property: styleProperty;
	label: string;
}>();
</script>
