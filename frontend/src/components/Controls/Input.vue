<template>
	<div class="relative w-full">
		<FormControl
			:type="type"
			@update:modelValue="($event: string | number | boolean) => emit('update:modelValue', $event)"
			@change="triggerUpdate"
			@paste="triggerUpdate"
			@cut="triggerUpdate"
			@focus="handleFocus"
			@input="($event: Event) => emit('input', ($event.target as HTMLInputElement).value)"
			autocomplete="off"
			:autofocus="autofocus"
			:disabled="disabled"
			v-bind="attrs"
			:modelValue="data">
			<template #prefix v-if="$slots.prefix">
				<slot name="prefix" />
			</template>
			<template #suffix v-if="$slots.suffix">
				<slot name="suffix" />
			</template>
			<template
				#suffix
				v-else-if="!['select', 'checkbox'].includes(type) && !hideClearButton && data && !disabled">
				<button
					class="cursor-pointer text-ink-gray-4 hover:text-ink-gray-5"
					tabindex="-1"
					@click="clearValue">
					<CrossIcon />
				</button>
			</template>
		</FormControl>
	</div>
</template>
<script lang="ts" setup>
import CrossIcon from "@/components/Icons/Cross.vue";
import { useDebounceFn, useVModel } from "@vueuse/core";
import { useAttrs } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue?: string | number | boolean | null;
		type?: string;
		hideClearButton?: boolean;
		autofocus?: boolean;
		disabled?: boolean;
		selectOnFocus?: boolean;
	}>(),
	{
		type: "text",
		modelValue: "",
		selectOnFocus: true,
	},
);
const emit = defineEmits(["update:modelValue", "input"]);
const data = useVModel(props, "modelValue", emit);

defineOptions({
	inheritAttrs: false,
});

const attrs = useAttrs();

const clearValue = () => {
	data.value = "";
};

const triggerUpdate = useDebounceFn(($event: Event) => {
	if (props.type === "checkbox") {
		emit("update:modelValue", ($event.target as HTMLInputElement).checked);
	} else {
		emit("update:modelValue", ($event.target as HTMLInputElement).value);
	}
}, 100);

const handleFocus = ($event: Event) => {
	if (props.selectOnFocus && !props.disabled && props.type !== "checkbox") {
		const target = $event.target as HTMLInputElement;
		setTimeout(() => {
			target.select();
		}, 0);
	}
};
</script>
