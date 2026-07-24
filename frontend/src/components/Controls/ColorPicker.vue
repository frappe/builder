<template>
	<Popover
		ref="colorPickerPopover"
		v-if="renderMode === 'popover'"
		:placement="placement"
		:offset="offset"
		:portal-to="portalTo"
		@open="emit('open')"
		@close="emit('close')"
		class="!block w-full">
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
				:showColorVariableOptions="showColorVariableOptions"
				renderMode="popover"
				@mousedown.stop
				@update:modelValue="emit('update:modelValue', $event)" />
		</template>
	</Popover>
	<ColorPickerContent
		v-else
		ref="contentRef"
		:modelValue="modelValue"
		:showInput="showInput"
		:showColorVariableOptions="showColorVariableOptions"
		renderMode="inline"
		@mousedown.stop
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
		showColorVariableOptions?: boolean;
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
	{ modelValue: null, showInput: false, showColorVariableOptions: true, placement: "left-start", renderMode: "popover", offset: 10 },
);

const emit = defineEmits(["update:modelValue", "open", "close"]);
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
