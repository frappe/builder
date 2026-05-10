<template>
	<div class="flex overflow-hidden whitespace-nowrap w-full" :title="text">
		<span ref="start" class="overflow-hidden min-w-0">{{ start }}</span>
		<span v-if="hasEllipsis">...</span>
		<span class="shrink-0">{{ end }}</span>
	</div>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from "vue";

const props = withDefaults(
	defineProps<{
		text: string;
		lettersAfterSlplit?: number;
	}>(),
	{
		lettersAfterSlplit: 16,
	},
);

const startSplitRef = useTemplateRef("start");

const splitIndex = computed(() => {
	return Math.floor(props.text.length - props.lettersAfterSlplit);
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