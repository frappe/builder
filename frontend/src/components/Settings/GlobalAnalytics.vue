<template>
	<div class="no-scrollbar h-full overflow-y-auto">
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
		<div class="mt-8">
			<h3 class="mb-4 text-lg font-medium">Top Pages</h3>
			<div
				v-if="analytics.loading"
				class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
				Loading...
			</div>
			<ListView
				v-else
				:columns="[
					{ label: 'Route', key: 'route', width: '70%' },
					{ label: 'Total Views', key: 'view_count' },
					{ label: 'Unique Views', key: 'unique_view_count' },
				]"
				:options="{ selectable: false, emptyState: {} }"
				:rows="analyticsData.top_pages"
				row-key="route" />
		</div>
	</div>
</template>

<script setup lang="ts">
import AnalyticsFilters from "@/components/Settings/AnalyticsFilters.vue";
import AnalyticsOverview from "@/components/Settings/AnalyticsOverview.vue";
import { useAnalytics } from "@/composables/useAnalytics";
import { ListView } from "frappe-ui";

const { range, interval, analyticsData, chartConfig, analytics } = useAnalytics({
	apiUrl: "builder.api.get_overall_analytics",
	initialRange: "last_7_days",
	initialInterval: "daily",
});
</script>
