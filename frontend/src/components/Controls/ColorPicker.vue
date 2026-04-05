<template>
	<Popover
		ref="colorPickerPopover"
		v-if="renderMode === 'popover'"
		:placement="placement"
		:offset="offset"
		class="!block w-full"
		popoverClass="!min-w-fit">
		<template #target="{ togglePopover, isOpen }">
			<slot
				name="target"
				:togglePopover="
					() => {
						togglePopover();
						contentRef?.syncPositions();
					}
				"
				:isOpen="isOpen"></slot>
		</template>
		<template #body>
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
import { ref } from "vue";
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
const contentRef = ref<InstanceType<typeof ColorPickerContent> | null>(null);

function togglePopover(open?: boolean) {
	if (open === undefined || open) {
		colorPickerPopover.value?.open();
	} else {
		colorPickerPopover.value?.close();
	}
}

defineExpose({ togglePopover });
</script>
