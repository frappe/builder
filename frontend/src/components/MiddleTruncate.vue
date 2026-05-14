<template>
	<component :is="as" class="flex w-full overflow-hidden whitespace-nowrap" :title="text">
		<span ref="start" class="min-w-0 overflow-hidden">{{ start }}</span>
		<span v-if="hasEllipsis">...</span>
		<span class="shrink-0">{{ end }}</span>
	</component>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watchEffect } from "vue";

const props = withDefaults(
	defineProps<{
		text: string;
		lettersAfterSplit?: number;
		as?: string;
	}>(),
	{
		lettersAfterSplit: 16,
		as: "div",
	},
);

const startSplitRef = useTemplateRef("start");

const splitIndex = computed(() => {
	return Math.floor(props.text.length - props.lettersAfterSplit);
});

const start = computed(() => {
	return props.text.slice(0, splitIndex.value);
});

const end = computed(() => {
	return props.text.slice(splitIndex.value);
});

const hasEllipsis = ref(false);

watchEffect((onCleanup) => {
	const el = startSplitRef.value;
	if (!el) {
		hasEllipsis.value = false;
		return;
	}

	const updateEllipsis = () => {
		hasEllipsis.value = el.scrollWidth > el.clientWidth;
	};

	updateEllipsis();

	const resizeObserver = new ResizeObserver(updateEllipsis);
	resizeObserver.observe(el);

	onCleanup(() => {
		resizeObserver.disconnect();
	});
});
</script>
