<template>
	<div class="flex w-full overflow-hidden whitespace-nowrap" :title="text">
		<span ref="start" class="min-w-0 overflow-hidden">{{ start }}</span>
		<span v-if="hasEllipsis">...</span>
		<span class="shrink-0">{{ end }}</span>
	</div>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from "vue";

const props = withDefaults(
	defineProps<{
		text: string;
		lettersAfterSplit?: number;
	}>(),
	{
		lettersAfterSplit: 16,
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

const hasEllipsis = computed(() => {
	if (startSplitRef.value) return startSplitRef.value.scrollWidth > startSplitRef.value.clientWidth;
	return false;
});
</script>
