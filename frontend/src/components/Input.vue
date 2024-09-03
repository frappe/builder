<template>
	<div class="relative w-full">
		<FormControl
			class="relative [&>div>input]:dark:border-zinc-700 [&>div>input]:dark:bg-zinc-800 [&>div>input]:dark:text-zinc-200 [&>div>input]:dark:focus:border-zinc-600 [&>div>input]:dark:focus:bg-zinc-700 [&>div>select]:pr-7 [&>div>select]:text-sm [&>div>select]:text-gray-800 [&>div>select]:dark:border-zinc-700 [&>div>select]:dark:bg-zinc-800 [&>div>select]:dark:text-zinc-200 [&>div>select]:dark:focus:bg-zinc-700 [&>label]:text-sm [&>label]:text-gray-700 [&>label]:dark:text-zinc-200 [&>textarea]:focus-visible:ring-zinc-700 [&>textarea]:dark:border-zinc-700 [&>textarea]:dark:bg-zinc-800 [&>textarea]:dark:text-zinc-200 [&>textarea]:dark:focus:border-zinc-600 [&>textarea]:dark:focus:bg-zinc-700"
			:type="type"
			:class="{
				'text-sm [&>div>input]:pr-5': !['select', 'checkbox'].includes(type) && !hideClearButton,
			}"
			@change="
				($event: Event) => {
					console.log($event);
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
			class="absolute bottom-[3px] right-[1px] cursor-pointer p-1 text-gray-500 dark:text-zinc-400"
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
