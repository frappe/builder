<template>
	<div>
		<h3 class="text-xl-medium mb-4 text-ink-gray-7">Top Clicks</h3>
		<div v-if="loading" class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
			Loading...
		</div>
		<ListView
			v-else-if="rows.length"
			class="!w-auto"
			:columns="[
				{ label: 'Target', key: 'label', width: '50%' },
				{ label: 'Clicks', key: 'clicks', align: 'right' },
				{ label: 'CTR', key: 'ctr_label', align: 'right' },
			]"
			:options="{ selectable: false, emptyState: {}, showTooltip: false }"
			:rows="rows"
			row-key="label" />
		<AnalyticsEmptyState
			v-else
			title="No clicks tracked yet"
			hint="Clicks on links and buttons will appear here." />
	</div>
</template>

<script setup lang="ts">
import AnalyticsEmptyState from "@/components/Settings/AnalyticsEmptyState.vue";
import type { CTRElement } from "@/composables/useAnalytics";
import { ListView } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ elements: CTRElement[]; loading?: boolean }>();

const rows = computed(() => props.elements.map((el) => ({ ...el, ctr_label: `${el.ctr}%` })));
</script>
