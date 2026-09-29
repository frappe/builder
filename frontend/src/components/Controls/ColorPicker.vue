<template>
	<Popover
		v-if="renderMode === 'popover'"
		:side="side"
		:align="align"
		:offset="offset"
		:portal-to="portalTo"
		bare
		:open="isOpen"
		@update:open="onUpdateOpen">
		<template #trigger>
			<div class="w-full" v-bind="$attrs" @click.capture="onAnchorClick">
				<slot name="target" :togglePopover="togglePopover" :isOpen="isOpen"></slot>
			</div>
		</template>
		<ColorPickerContent
			ref="contentRef"
			:modelValue="modelValue"
			:showInput="showInput"
			renderMode="popover"
			@update:modelValue="emit('update:modelValue', $event)" />
	</Popover>
	<ColorPickerContent
		v-else
		v-bind="$attrs"
		ref="contentRef"
		:modelValue="modelValue"
		:showInput="showInput"
		renderMode="inline"
		@update:modelValue="emit('update:modelValue', $event)" />
</template>
<script setup lang="ts">
import { useAnchoredPopover } from "@/utils/useAnchoredPopover";
import { Popover } from "frappe-ui";
import { computed, ref } from "vue";
import ColorPickerContent from "./ColorPickerContent.vue";

// attributes belong on the trigger row (or the inline picker), never on the popover shell
defineOptions({ inheritAttrs: false });

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

const emit = defineEmits(["update:modelValue", "open", "close"]);
const contentRef = ref<InstanceType<typeof ColorPickerContent> | null>(null);

const side = computed(() => props.placement.split("-")[0] as "top" | "bottom" | "left" | "right");
const align = computed(() => (props.placement.split("-")[1] ?? "center") as "start" | "center" | "end");

// bank the color the picker closed on into the recently used swatches
const { isOpen, toggle, onAnchorClick, onUpdateOpen } = useAnchoredPopover((open) => {
	if (!open) contentRef.value?.commitRecentColor();
	emit(open ? "open" : "close");
});

// event handlers bind this directly, so drop the event they pass
function togglePopover(open?: boolean | Event) {
	toggle(open);
	contentRef.value?.syncPositions();
}

defineExpose({
	togglePopover,
	isOpen,
	commitRecentColor: () => contentRef.value?.commitRecentColor(),
});
</script>
