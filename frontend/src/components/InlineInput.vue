<template>
	<div class="flex items-center mt-3 justify-between">
		<span class="text-gray-600 font-bold text-[10px] uppercase inline-block ml-2 dark:text-zinc-400">
			<slot></slot>
		</span>
		<Input :type="type" :value="value" :options="options" @change="handleChange" class="dark:bg-zinc-700 rounded-md dark:text-zinc-50 dark:focus:bg-zinc-600"/>
	</div>
</template>
<script setup>
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
	options: {
		type: Array,
		default: () => []
	}
});

const emit = defineEmits(["updateValue"]);

const handleChange = (value) => {
	emit("updateValue", value);
}

</script>