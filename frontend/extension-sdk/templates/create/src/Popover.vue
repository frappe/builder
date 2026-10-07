<template>
	<div class="flex h-full min-h-0 flex-col bg-surface-base text-ink-gray-8">
		<div class="min-h-0 flex-1 overflow-auto p-4">
			<pre class="whitespace-pre-wrap font-mono text-p-xs text-ink-gray-7">{{ rawContext }}</pre>
		</div>

		<div class="border-t border-outline-gray-2 p-4">
			<p v-if="disabledReason" class="mb-2 text-p-xs text-ink-gray-5">{{ disabledReason }}</p>
			<p v-else-if="errorMessage" class="mb-2 text-p-xs text-red-600">{{ errorMessage }}</p>
			<Button
				class="w-full"
				label="Add Builder icon"
				:disabled="Boolean(disabledReason)"
				:loading="isAdding"
				@click="addBuilderIcon" />
		</div>
	</div>
</template>

<script setup lang="ts">
import builder from "frappe-builder-extension-sdk";
import { useBuilderContext } from "frappe-builder-extension-sdk/vue";
import { Button } from "frappe-ui";
import { computed, ref } from "vue";
import builderIcon from "./icon.svg?raw";

const context = useBuilderContext([
	"selection",
	"breakpoint",
	"editingMode",
	"readOnly",
	"isAIEnabled",
	"page",
	"site",
]);
const isAdding = ref(false);
const errorMessage = ref("");

const disabledReason = computed(() => {
	if (context.readOnly) return "The page is read only.";
	if (context.selection.count === 0) return "Select one block first.";
	if (context.selection.count > 1) return "Select only one block.";
	if (!context.selection.blockId) return "The selected block is unavailable.";
	return "";
});

const rawContext = computed(() =>
	JSON.stringify(
		{
			selection: { ...context.selection },
			breakpoint: context.breakpoint,
			editingMode: context.editingMode,
			readOnly: context.readOnly,
			isAIEnabled: context.isAIEnabled,
			page: context.page,
			site: context.site,
		},
		null,
		2,
	),
);

const addBuilderIcon = async () => {
	if (disabledReason.value || !context.selection.blockId) return;

	isAdding.value = true;
	errorMessage.value = "";
	try {
		await builder.block.insert(context.selection.blockId, {
			element: "div",
			attributes: { "aria-label": "Builder icon" },
			styles: { display: "inline-flex", width: "32px", height: "32px" },
			innerHTML: builderIcon,
		});
		await builder.ui.toast("Builder icon added as the last child.", { type: "success" });
	} catch (error) {
		errorMessage.value = error instanceof Error ? error.message : "Could not add the Builder icon.";
	} finally {
		isAdding.value = false;
	}
};
</script>
