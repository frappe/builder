<template>
	<Popover
		ref="colorPickerPopover"
		v-if="renderMode === 'popover'"
		:side="side"
		:align="align"
		:offset="offset"
		bare>
		<template #trigger="slotProps">
			<slot name="trigger" v-bind="slotProps"></slot>
		</template>
		<template #default>
			<ColorPickerContent
				:modelValue="modelValue"
				:showInput="showInput"
				renderMode="popover"
				@update:modelValue="emit('update:modelValue', $event)" />
		</template>
	</Popover>
	<ColorPickerContent
		v-else
		:modelValue="modelValue"
		:showInput="showInput"
		renderMode="inline"
		@update:modelValue="emit('update:modelValue', $event)" />
</template>
<script setup lang="ts">
import { Popover } from "frappe-ui";
import { computed, ref } from "vue";
import ColorPickerContent from "./ColorPickerContent.vue";

type CSSColorValue = HashString | RGBString | `var(--${string})`;

const props = withDefaults(
	defineProps<{
		modelValue?: CSSColorValue | null;
		showInput?: boolean;
		placement?:
			| "bottom-start"
			| "top-start"
			| "top-end"
			| "bottom-end"
			| "right-start"
			| "right-end"
			| "left-start"
			| "left-end"
			| "bottom"
			| "top"
			| "right"
			| "left";
		renderMode?: "popover" | "inline";
		offset?: number;
	}>(),
	{ modelValue: null, showInput: false, placement: "left-start", renderMode: "popover", offset: 10 },
);

const emit = defineEmits(["update:modelValue"]);
const colorPickerPopover = ref<InstanceType<typeof Popover> | null>(null);

const side = computed(() => props.placement.split("-")[0] as "top" | "bottom" | "left" | "right");
const align = computed(() => (props.placement.split("-")[1] ?? "center") as "start" | "center" | "end");

function togglePopover(open?: boolean) {
	if (open === undefined || open) {
		colorPickerPopover.value?.open();
	} else {
		colorPickerPopover.value?.close();
	}
}

defineExpose({ togglePopover });
</script>
