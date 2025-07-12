<template>
	<PropertyControl
		:component="Autocomplete"
		:styleProperty="property"
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
		:unitOptions="['px', '%', 'vw', 'vh']"></PropertyControl>
</template>
<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";

defineProps<{
	property: styleProperty;
	label: string;
}>();
</script>
