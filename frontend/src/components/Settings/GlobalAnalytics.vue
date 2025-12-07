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
					@update:route="(val) => (route = val)"
					@update:customDateRange="(val) => (customDateRange = val)" />
			</template>
		</AnalyticsOverview>
		<div class="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2">
			<div>
				<h3 class="mb-4 text-lg font-medium">Top Pages</h3>
				<div
					v-if="analytics.loading"
					class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
					Loading...
				</div>
				<ListView
					class="!w-auto"
					v-else
					:columns="[
						{ label: 'Route', key: 'route', width: '60%' },
						{ label: 'Views', key: 'view_count', align: 'right' },
					]"
					:options="{
						selectable: false,
						emptyState: {},
						showTooltip: false,
						onRowClick: onPageRowClick,
					}"
					:rows="processedAnalyticsData.top_pages"
					row-key="route" />
			</div>
			<div>
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
									onError: (e) => {
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
	</div>
</template>

<script setup lang="ts">
import AnalyticsFilters from "@/components/Settings/AnalyticsFilters.vue";
import AnalyticsOverview from "@/components/Settings/AnalyticsOverview.vue";
import { useAnalytics } from "@/composables/useAnalytics";
import { ListView } from "frappe-ui";
import { h } from "vue";

const {
	range,
	route,
	customDateRange,
	analyticsData,
	chartConfigWithEvents,
	processedAnalyticsData,
	analytics,
	onPageRowClick,
} = useAnalytics({
	apiUrl: "builder.api.get_overall_analytics",
	initialRange: "last_30_days",
});
</script>
