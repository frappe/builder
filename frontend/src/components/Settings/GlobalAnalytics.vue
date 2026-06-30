<template>
	<div class="no-scrollbar h-full overflow-y-auto overflow-x-hidden pr-1">
		<TrackingDisabledNotice v-if="trackingEnabled === false" />
		<template v-else>
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
			<div class="mt-8">
				<h3 class="text-xl-medium mb-4 text-ink-gray-7">Top Pages</h3>
				<div
					v-if="analytics.loading"
					class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
					Loading...
				</div>
				<ListView
					class="!w-auto"
					v-else-if="processedAnalyticsData.top_pages?.length"
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
				<AnalyticsEmptyState v-else title="No page views yet" />
			</div>
			<div class="mt-8">
				<TopReferrersList :rows="processedAnalyticsData.top_referrers" :loading="analytics.loading" />
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import AnalyticsEmptyState from "@/components/Settings/AnalyticsEmptyState.vue";
import AnalyticsFilters from "@/components/Settings/AnalyticsFilters.vue";
import AnalyticsOverview from "@/components/Settings/AnalyticsOverview.vue";
import TopReferrersList from "@/components/Settings/TopReferrersList.vue";
import TrackingDisabledNotice from "@/components/Settings/TrackingDisabledNotice.vue";
import { useAnalytics } from "@/composables/useAnalytics";
import { ListView } from "frappe-ui";

const {
	range,
	route,
	customDateRange,
	trackingEnabled,
	analyticsData,
	chartConfigWithEvents,
	processedAnalyticsData,
	analytics,
	onPageRowClick,
} = useAnalytics({
	apiUrl: "builder.api.get_overall_analytics",
	initialRange: "last_30_days",
	routePersistKey: "builderGlobalAnalyticsRoute",
});
</script>
