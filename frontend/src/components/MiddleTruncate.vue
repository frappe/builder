<template>
	<component :is="as" class="flex w-full overflow-hidden whitespace-nowrap" :title="text">
		<span class="truncate min-w-0 break-words">{{ start }}</span>
		<span class="shrink-0">{{ end }}</span>
	</component>
</template>

<script setup lang="ts">
import { computed } from "vue";

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

const splitIndex = computed(() => {
	return Math.floor(props.text.length - props.lettersAfterSplit);
});

const start = computed(() => {
	return props.text.slice(0, splitIndex.value);
});

const end = computed(() => {
	return props.text.slice(splitIndex.value);
});
</script>
