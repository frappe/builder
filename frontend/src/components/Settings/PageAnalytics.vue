<template>
	<div class="no-scrollbar h-full overflow-y-auto overflow-x-hidden pr-1">
		<AnalyticsOverview
			:data="analyticsData"
			:chartConfig="chartConfigWithEvents"
			:loading="analytics.loading">
			<template #filters>
				<AnalyticsFilters
					:range="range"
					:route="route"
					:customDateRange="customDateRange"
					@update:range="(val) => (range = val)"
					@update:route="(val) => (route = val?.value)"
					@update:customDateRange="(val) => (customDateRange = val)" />
			</template>
		</AnalyticsOverview>
		<div class="mt-8">
			<h3 class="mb-4 text-lg font-medium">Top Referrers</h3>
			<div
				v-if="analytics.loading"
				class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
				Loading...
			</div>
			<ListView
				v-else
				class="!w-auto"
				:columns="[
					{
						label: 'Domain',
						key: 'domain',
						width: '60%',
						prefix: ({ row }: { row: any }) => {
							return h('img', {
								src: `https://${row.domain}/favicon.ico`,
								alt: row.domain,
								class: 'inline-block mr-2 w-5 h-5 align-middle rounded',
								onError: (e: Event) => {
									const img = e.target as HTMLImageElement | null;
									if (img) {
										img.src = '/assets/builder/images/fallback-favicon.ico';
									}
								},
							});
						},
					},
					{ label: 'Count', key: 'count', align: 'right' },
				]"
				:options="{ selectable: false, emptyState: {} }"
				:rows="processedAnalyticsData.top_referrers"
				row-key="domain" />
		</div>
	</div>
</template>

<script setup lang="ts">
import AnalyticsFilters from "@/components/Settings/AnalyticsFilters.vue";
import AnalyticsOverview from "@/components/Settings/AnalyticsOverview.vue";
import { useAnalytics } from "@/composables/useAnalytics";
import usePageStore from "@/stores/pageStore";
import { ListView } from "frappe-ui";
import { h } from "vue";

const pageStore = usePageStore();
const {
	range,
	interval,
	route,
	customDateRange,
	analyticsData,
	chartConfigWithEvents,
	processedAnalyticsData,
	analytics,
} = useAnalytics({
	apiUrl: "builder.api.get_page_analytics",
	initialRange: "last_30_days",
	initialRouteFilterType: "exact",
	initialRoute: pageStore.getResolvedPageURL(false),
});
</script>
