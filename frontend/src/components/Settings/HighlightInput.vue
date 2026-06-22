<template>
	<div class="relative w-full">
		<!-- Real input drives caret, focus ring and bg; its own text is transparent so the colored mirror shows through. -->
		<input
			ref="inputRef"
			type="text"
			autocomplete="off"
			spellcheck="false"
			:value="modelValue"
			:class="[cellBoxClass, editableInputClass, 'text-transparent']"
			style="caret-color: var(--ink-gray-8)"
			v-bind="$attrs"
			@input="onInput"
			@scroll="syncScroll" />
		<div
			ref="mirrorRef"
			aria-hidden="true"
			:class="[
				cellBoxClass,
				'pointer-events-none absolute inset-0 flex items-center overflow-hidden whitespace-pre',
			]">
			<span v-if="modelValue" class="text-ink-gray-8" v-html="highlighted" />
			<span v-else class="text-ink-gray-4">{{ placeholder }}</span>
		</div>
	</div>
</template>
<script setup lang="ts">
import { cellBoxClass, editableInputClass } from "@/utils/editableTable";
import { highlightSource, highlightTarget } from "@/utils/redirectSyntax";
import { computed, ref } from "vue";

const props = withDefaults(
	defineProps<{ modelValue: string; placeholder?: string; kind?: "source" | "target" }>(),
	{ kind: "source" },
);
const emit = defineEmits(["update:modelValue"]);

defineOptions({ inheritAttrs: false });

const inputRef = ref<HTMLInputElement | null>(null);
const mirrorRef = ref<HTMLElement | null>(null);

const highlighted = computed(() =>
	props.kind === "target" ? highlightTarget(props.modelValue) : highlightSource(props.modelValue),
);

const onInput = (event: Event) => emit("update:modelValue", (event.target as HTMLInputElement).value);

// Keep the mirror aligned with the input while typing past its width.
const syncScroll = () => {
	if (inputRef.value && mirrorRef.value) mirrorRef.value.scrollLeft = inputRef.value.scrollLeft;
};

defineExpose({ focus: () => inputRef.value?.focus() });
</script>
