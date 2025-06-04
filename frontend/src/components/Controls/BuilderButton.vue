<template>
	<Button :variant="variant" :class="classes"><slot /></Button>
</template>
<script lang="ts" setup>
import { Button } from "frappe-ui";
import { computed } from "vue";

const props = withDefaults(
	defineProps<{
		variant?: string;
	}>(),
	{
		variant: "subtle",
	},
);

const classes = computed(() => {
	const _classes = [];
	if (props.variant === "solid") {
		_classes.push([
			"bg-surface-gray-7",
			"!text-ink-white",
			"hover:bg-surface-gray-6",
			"active:bg-surface-gray-5",
			// style for disabled button
			"disabled:bg-surface-gray-4",
			"disabled:text-ink-gray-8",
		]);
	} else if (props.variant === "subtle") {
		_classes.push([
			"bg-surface-gray-2",
			"text-ink-gray-7",
			"hover:bg-surface-gray-3",
			"active:bg-surface-gray-4",
		]);
	}
	return _classes;
});
</script>
