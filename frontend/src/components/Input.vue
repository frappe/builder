<template>
	<div class="relative w-full">
		<FormControl
			class="relative [&>div>input]:focus-visible:ring-zinc-700 [&>div>input]:dark:border-zinc-700 [&>div>input]:dark:bg-zinc-800 [&>div>input]:dark:text-zinc-200 [&>div>input]:dark:focus:border-zinc-600 [&>div>input]:dark:focus:bg-zinc-700 [&>div>input]:dark:focus-visible:outline-0 [&>div>input]:dark:focus-visible:ring-zinc-700 [&>div>select]:text-sm [&>div>select]:text-gray-800 [&>div>select]:dark:border-zinc-700 [&>div>select]:dark:bg-zinc-800 [&>div>select]:dark:text-zinc-200 [&>div>select]:dark:focus:bg-zinc-700"
			:type="type"
			:class="{
				'text-sm [&>div>input]:pr-5': !['select', 'checkbox'].includes(type),
			}"
			@change="
				($event: Event) => {
					if (type === 'checkbox') {
						emit('update:modelValue', ($event.target as HTMLInputElement).checked);
					} else {
						emit('update:modelValue', ($event.target as HTMLInputElement).value);
					}
				}
			"
			@input="($event: Event) => emit('input', ($event.target as HTMLInputElement).value)"
			autocomplete="off"
			v-bind="attrs"
			:modelValue="data"></FormControl>
		<div
			class="absolute right-[1px] top-[3px] cursor-pointer p-1 text-gray-700 dark:text-zinc-300"
			@click="clearValue"
			v-if="!['select', 'checkbox'].includes(type) && !hideClearButton"
			v-show="data">
			<CrossIcon />
		</div>
	</div>
</template>
<script lang="ts" setup>
import { useVModel } from "@vueuse/core";
import { useAttrs } from "vue";
import CrossIcon from "./Icons/Cross.vue";

const props = defineProps(["modelValue", "type", "hideClearButton"]);
const emit = defineEmits(["update:modelValue", "input"]);
const data = useVModel(props, "modelValue", emit);

defineOptions({
	inheritAttrs: false,
});

const attrs = useAttrs();

const clearValue = () => {
	data.value = "";
};
</script>
