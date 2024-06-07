<template>
	<FormControl
		class="[&>div>input]:focus-visible:ring-zinc-700 [&>div>input]:dark:border-zinc-700 [&>div>input]:dark:bg-zinc-800 [&>div>input]:dark:text-zinc-200 [&>div>input]:dark:focus:border-zinc-600 [&>div>input]:dark:focus:bg-zinc-700 [&>div>input]:dark:focus-visible:outline-0 [&>div>input]:dark:focus-visible:ring-zinc-700 [&>div>select]:text-sm [&>div>select]:text-gray-800 [&>div>select]:dark:border-zinc-700 [&>div>select]:dark:bg-zinc-800 [&>div>select]:dark:text-zinc-200 [&>div>select]:dark:focus:bg-zinc-700"
		@input="($event: Event) => emit('update:modelValue', ($event.target as HTMLInputElement).value)"
		autocomplete="off"
		v-model="data" />
</template>
<script lang="ts" setup>
import { useVModel } from "@vueuse/core";

const props = defineProps(["modelValue"]);
const emit = defineEmits(["update:modelValue", "input"]);
const data = useVModel(props, "modelValue", emit);
</script>
