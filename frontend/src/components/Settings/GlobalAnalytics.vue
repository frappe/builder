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
			<div class="mt-8 flex flex-col gap-5 md:flex-row md:items-start">
				<div v-if="analytics.loading || processedAnalyticsData.top_pages?.length" class="flex-1">
					<h3 class="text-lg-medium mb-4 text-ink-gray-7">{{ __("Top Pages") }}</h3>
					<div
						v-if="analytics.loading"
						class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
						{{ __("Loading...") }}
					</div>
					<ListView
						class="!w-auto"
						v-else
						:columns="[
							{ label: __('Route'), key: 'route', width: '60%' },
							{ label: __('Views'), key: 'view_count', align: 'right' },
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
				<TopReferrersList
					class="flex-1"
					:rows="processedAnalyticsData.top_referrers"
					:loading="analytics.loading" />
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
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
