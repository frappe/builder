<template>
	<div v-if="loading || rows.length">
		<h3 class="text-lg-medium mb-4 text-ink-gray-7">{{ __("Top Clicks") }}</h3>
		<div v-if="loading" class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
			{{ __("Loading...") }}
		</div>
		<ListView
			v-else
			class="!w-auto"
			:columns="[
				{ label: __('Target'), key: 'label', width: '50%' },
				{ label: __('Clicks'), key: 'clicks', align: 'right' },
				{ label: __('CTR'), key: 'ctr_label', align: 'right' },
			]"
			:options="{ selectable: false, emptyState: {}, showTooltip: false, onRowClick: highlightBlock }"
			:rows="rows"
			row-key="blockId" />
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { findBlockInTree } from "@/utils/block/tree";
import type { CTRElement } from "@/composables/useAnalytics";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { ListView } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ elements: CTRElement[]; loading?: boolean }>();

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const rows = computed(() => props.elements.slice(0, 10).map((el) => ({ ...el, ctr_label: `${el.ctr}%` })));

const highlightBlock = (row: CTRElement) => {
	const rootBlock = canvasStore.getRootBlock();
	if (!rootBlock || !row.blockId) return;
	const block = findBlockInTree(row.blockId, [rootBlock]);
	if (!block) return;
	// The analytics dialog covers the canvas, so close it before revealing the block.
	builderStore.showSettingsDialog = false;
	canvasStore.selectBlock(block, null, false, true);
};
</script>
