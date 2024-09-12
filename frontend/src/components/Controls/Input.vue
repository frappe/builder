<template>
	<div class="relative w-full">
		<FormControl
			:class="classes"
			:type="type"
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
			class="absolute bottom-[3px] right-[1px] cursor-pointer p-1 text-text-icons-gray-4 hover:text-text-icons-gray-5"
			@click="clearValue"
			v-if="!['select', 'checkbox'].includes(type) && !hideClearButton"
			v-show="data">
			<CrossIcon />
		</div>
	</div>
</template>
<script lang="ts" setup>
import CrossIcon from "@/components/Icons/Cross.vue";
import { useVModel } from "@vueuse/core";
import { computed, useAttrs } from "vue";

const props = defineProps(["modelValue", "type", "hideClearButton"]);
const emit = defineEmits(["update:modelValue", "input"]);
const data = useVModel(props, "modelValue", emit);

defineOptions({
	inheritAttrs: false,
});

const classes = computed(() => {
	const _classes = [];
	if (!["select", "checkbox"].includes(props.type) && !props.hideClearButton) {
		_classes.push("[&>div>input]:pr-7");
	}
	if (props.type === "select") {
		_classes.push(
			...[
				"[&>div>select]:text-text-icons-8",
				"[&>label]:text-text-outline-gray-7",
				"[&>div>select]:border-outline-gray-1",
				"[&>div>select]:bg-surface-gray-2",
				"[&>div>select]:pr-7",
				"[&>div>select]:focus:border-outline-gray-3",
				"[&>div>select]:focus:bg-surface-gray-1",
			],
		);
	} else if (props.type === "textarea") {
		_classes.push([
			"[&>textarea]:border-outline-gray-1",
			"[&>textarea]:bg-surface-gray-2",
			"[&>textarea]:text-text-icons-gray-8",
			"[&>textarea]:focus:border-outline-gray-3",
			"[&>textarea]:focus:bg-surface-gray-1",
		]);
	} else {
		_classes.push([
			"[&>div>input]:focus:!bg-surface-gray-1",
			"[&>div>input]:focus-visible:!bg-surface-gray-1",
			"[&>div>input]:border-outline-gray-1",
			"[&>div>input]:bg-surface-gray-2",
			"[&>div>input]:text-text-icons-gray-8",
			"[&>div>input]:focus:border-outline-gray-3",
			"[&>div>input]:pr-5 text-sm",
			"[&>div>input]:hover:border-outline-gray-2",
			"[&>div>input]:hover:bg-surface-gray-1",
		]);
	}
	return _classes;
});

const attrs = useAttrs();

const clearValue = () => {
	data.value = "";
};
</script>
