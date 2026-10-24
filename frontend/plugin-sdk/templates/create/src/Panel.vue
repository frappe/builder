<template>
	<div class="flex flex-col gap-3 p-4 text-p-sm text-ink-gray-7">
		<p>{{ pageStore.activePage?.page_title ?? "No page is open." }}</p>
		<p v-if="disabledReason" class="text-p-xs text-ink-gray-5">{{ disabledReason }}</p>
		<Button label="Add Builder icon" :disabled="Boolean(disabledReason)" @click="addBuilderIcon" />
	</div>
</template>

<script setup lang="ts">
import { blockController, useBuilderStore, usePageStore } from "builder";
import { Button, toast } from "frappe-ui";
import { computed } from "vue";
import builderIcon from "./icon.svg?raw";

const pageStore = usePageStore();
const builderStore = useBuilderStore();

const disabledReason = computed(() => {
	const selected = blockController.getSelectedBlocks();
	if (builderStore.readOnlyMode) return "The page is read only.";
	if (selected.length !== 1) return "Select one block first.";
	if (!selected[0].canHaveChildren()) return "The selected block cannot hold a child.";
	return "";
});

const addBuilderIcon = () => {
	blockController.getFirstSelectedBlock().addChild({
		element: "div",
		attributes: { "aria-label": "Builder icon" },
		baseStyles: { display: "inline-flex", width: "32px", height: "32px" },
		innerHTML: builderIcon,
	});
	toast.success("Builder icon added as the last child.");
};
</script>
