<template>
	<div class="flex gap-2">
		<Select size="sm" v-model="modelInterval" :options="intervalOptions" />
		<Select size="sm" v-model="modelRange" :options="rangeOptions" />
	</div>
</template>

<script setup lang="ts">
import { Select } from "frappe-ui";
import { computed } from "vue";

const props = defineProps({
	interval: {
		type: String,
		required: true,
	},
	range: {
		type: String,
		required: true,
	},
	intervalOptions: {
		type: Array,
		required: true,
	},
	rangeOptions: {
		type: Array,
		required: true,
	},
});
const emit = defineEmits(["update:interval", "update:range"]);

const modelInterval = computed({
	get: () => props.interval,
	set: (val) => emit("update:interval", val),
});
const modelRange = computed({
	get: () => props.range,
	set: (val) => emit("update:range", val),
});
</script>
