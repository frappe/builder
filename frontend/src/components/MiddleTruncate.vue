<template>
	<component :is="as" class="flex w-full overflow-hidden whitespace-nowrap" :title="text">
		<span class="min-w-4 truncate">{{ textParts.join(".") }}</span>
		<span class="" v-if="textParts.length > 1">{{ textParts[textParts.length - 1] }}</span>
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

const textParts = computed(() => {
	return props.text.split(".");
});
</script>
