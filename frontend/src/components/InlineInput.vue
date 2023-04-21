<template>
	<div class="flex items-center mt-3 justify-between">
		<span class="text-gray-600 font-bold text-[10px] uppercase inline-block ml-2 dark:text-zinc-400">
			<slot />
		</span>
		<Input
			:type="type" :value="value" :options="options"
			@change="handleChange"
			class="text-sm text-gray-800 dark:bg-zinc-800 rounded-md dark:text-zinc-200 dark:focus:bg-zinc-700 min-w-[60%]" />
	</div>
</template>
<script setup lang="ts">
import { Input } from "frappe-ui";

defineProps({
	value: {
		type: String,
		default: ""
	},
	type: {
		type: String,
		default: "text"
	},
	unitOptions: {
		type: Array,
		default: () => []
	},
	options: {
		type: Array,
		default: () => []
	}
});

const emit = defineEmits(["updateValue"]);

const handleChange = (value: string | number | null) => {
	emit("updateValue", value);
}

</script>