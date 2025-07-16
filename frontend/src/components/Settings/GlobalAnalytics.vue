<template>
	<div class="no-scrollbar h-full overflow-y-auto overflow-x-hidden">
		<AnalyticsOverview :data="analyticsData" :chartConfig="chartConfig" :loading="analytics.loading">
			<template #filters>
				<AnalyticsFilters
					:interval="interval"
					:range="range"
					:intervalOptions="[
						{ label: 'Hourly', value: 'hourly' },
						{ label: 'Daily', value: 'daily' },
						{ label: 'Weekly', value: 'weekly' },
						{ label: 'Monthly', value: 'monthly' },
					]"
					:rangeOptions="[
						{ label: 'Today', value: 'today' },
						{ label: 'Last 7 Days', value: 'last_7_days' },
						{ label: 'Last 30 Days', value: 'last_30_days' },
						{ label: 'This Year', value: 'this_year' },
					]"
					@update:interval="(val) => (interval = val)"
					@update:range="(val) => (range = val)" />
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
							prefix: ({ row }) => {
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
import { shortenNumber } from "@/utils/helpers";
import { ListView } from "frappe-ui";
import { computed, h } from "vue";

const { range, interval, analyticsData, chartConfig, analytics } = useAnalytics({
	apiUrl: "builder.api.get_overall_analytics",
	initialRange: "last_7_days",
	initialInterval: "daily",
});

const processedAnalyticsData = computed(() => {
	return {
		top_referrers: analyticsData.value.top_referrers?.map((referrer) => ({
			...referrer,
			count: shortenNumber(referrer.count),
		})),
		top_pages: analyticsData.value.top_pages?.map((page) => ({
			...page,
			view_count: shortenNumber(page.view_count),
		})),
	};
});

const onPageRowClick = (row: { route: string }) => {
	window.open(`/${row.route}`, "_blank");
};
</script>
