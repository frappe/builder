<template>
	<!-- Reuse frappe-ui's TextInput; only override its text colour and float a highlighted mirror on top. -->
	<div class="highlight-input w-full space-y-1.5">
		<div ref="root" class="relative w-full">
			<TextInput
				class="w-full"
				:modelValue="modelValue"
				type="text"
				:label="label"
				variant="outline"
				v-bind="$attrs"
				@update:modelValue="(val: string) => emit('update:modelValue', val)" />
			<div
				ref="mirror"
				aria-hidden="true"
				class="pointer-events-none absolute inset-0 flex items-center overflow-hidden whitespace-pre rounded border border-transparent px-2 text-base">
				<span v-if="modelValue" class="text-ink-gray-8" v-html="highlighted" />
				<span v-else class="text-ink-gray-4">{{ placeholder }}</span>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { highlightSource, highlightTarget } from "@/utils/redirectSyntax";
import { TextInput } from "frappe-ui";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = withDefaults(
	defineProps<{ modelValue: string; placeholder?: string; label?: string; kind?: "source" | "target" }>(),
	{ kind: "source" },
);
const emit = defineEmits(["update:modelValue"]);

defineOptions({ inheritAttrs: false });

const root = ref<HTMLElement | null>(null);
const mirror = ref<HTMLElement | null>(null);
let inputEl: HTMLInputElement | null = null;

const highlighted = computed(() =>
	(props.kind === "target" ? highlightTarget : highlightSource)(props.modelValue),
);

// Keep the mirror aligned with the input while typing past its width.
const syncScroll = () => {
	if (inputEl && mirror.value) mirror.value.scrollLeft = inputEl.scrollLeft;
};

onMounted(() => {
	inputEl = root.value?.querySelector("input") ?? null;
	inputEl?.addEventListener("scroll", syncScroll);
});
onBeforeUnmount(() => inputEl?.removeEventListener("scroll", syncScroll));

defineExpose({ focus: () => root.value?.querySelector("input")?.focus() });
</script>
<style scoped>
/* The real input drives caret, focus ring and bg; its glyphs are hidden so the mirror shows through. */
.highlight-input :deep(input) {
	color: transparent;
	caret-color: var(--ink-gray-8);
}
</style>
