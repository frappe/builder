<template>
	<Popover
		ref="colorPickerPopover"
		v-if="renderMode === 'popover'"
		:side="side"
		:align="align"
		:offset="offset"
		:portal-to="portalTo"
		@update:open="isOpen = $event"
		bare>
		<template #trigger="slotProps">
			<slot name="trigger" v-bind="slotProps"></slot>
		</template>
		<template #default>
			<ColorPickerContent
				ref="contentRef"
				:modelValue="modelValue"
				:showInput="showInput"
				renderMode="popover"
				@update:modelValue="emit('update:modelValue', $event)" />
		</template>
	</Popover>
	<ColorPickerContent
		v-else
		ref="contentRef"
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
		portalTo?: string | HTMLElement;
	}>(),
	{ modelValue: null, showInput: false, placement: "left-start", renderMode: "popover", offset: 10 },
);

const emit = defineEmits(["update:modelValue"]);
const colorPickerPopover = ref<InstanceType<typeof Popover> | null>(null);
const contentRef = ref<InstanceType<typeof ColorPickerContent> | null>(null);
const isOpen = ref(false);

const side = computed(() => props.placement.split("-")[0] as "top" | "bottom" | "left" | "right");
const align = computed(() => (props.placement.split("-")[1] ?? "center") as "start" | "center" | "end");

// event handlers bind this directly, so drop the event they pass
function togglePopover(open?: boolean | Event) {
	if (open instanceof Event) open = undefined;
	if (open == null) open = !isOpen.value;
	if (open) {
		colorPickerPopover.value?.open();
	} else {
		colorPickerPopover.value?.close();
	}
	contentRef.value?.syncPositions();
}

defineExpose({
	togglePopover,
	isOpen,
	hideOptions: () => contentRef.value?.hideOptions(),
});
</script>
