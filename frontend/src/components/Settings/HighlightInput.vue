<template>
	<div class="relative w-full">
		<!-- Native-looking input; its own text is transparent so the colored mirror shows through. -->
		<input
			ref="inputRef"
			type="text"
			autocomplete="off"
			spellcheck="false"
			:value="modelValue"
			class="h-7 w-full rounded border border-gray-100 bg-gray-100 px-2 py-1.5 text-base text-transparent caret-gray-800 transition-colors hover:border-gray-200 hover:bg-gray-200 focus:border-gray-500 focus:bg-white focus:shadow-sm focus:outline-none focus:ring-0 focus-visible:ring-2 focus-visible:ring-gray-400"
			v-bind="$attrs"
			@input="onInput"
			@scroll="syncScroll" />
		<div
			ref="mirrorRef"
			aria-hidden="true"
			class="pointer-events-none absolute inset-0 flex items-center overflow-hidden whitespace-pre rounded border border-transparent px-2 py-1.5 text-base text-gray-800">
			<span v-if="modelValue" v-html="highlighted" />
			<span v-else class="text-gray-500">{{ placeholder }}</span>
		</div>
	</div>
</template>
<script setup lang="ts">
import { highlightRedirectSyntax } from "@/utils/redirectSyntax";
import { computed, ref } from "vue";

const props = defineProps<{ modelValue: string; placeholder?: string }>();
const emit = defineEmits(["update:modelValue"]);

defineOptions({ inheritAttrs: false });

const inputRef = ref<HTMLInputElement | null>(null);
const mirrorRef = ref<HTMLElement | null>(null);

const highlighted = computed(() => highlightRedirectSyntax(props.modelValue));

const onInput = (event: Event) => emit("update:modelValue", (event.target as HTMLInputElement).value);

// Keep the mirror aligned with the input while typing past its width.
const syncScroll = () => {
	if (inputRef.value && mirrorRef.value) mirrorRef.value.scrollLeft = inputRef.value.scrollLeft;
};

defineExpose({ focus: () => inputRef.value?.focus() });
</script>
