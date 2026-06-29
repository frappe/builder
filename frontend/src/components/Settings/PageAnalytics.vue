<template>
	<div class="no-scrollbar h-full overflow-y-auto overflow-x-hidden pr-1">
		<TrackingDisabledNotice v-if="trackingEnabled === false" />
		<template v-else>
			<AnalyticsOverview
				:data="analyticsData"
				:chartConfig="chartConfigWithEvents"
				:loading="analytics.loading"
				:ctr="ctrData.ctr">
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
				<TopReferrersList :rows="processedAnalyticsData.top_referrers" :loading="analytics.loading" />
				<TopClicksList :elements="ctrData.elements" :loading="ctr?.loading" />
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import AnalyticsFilters from "@/components/Settings/AnalyticsFilters.vue";
import AnalyticsOverview from "@/components/Settings/AnalyticsOverview.vue";
import TopClicksList from "@/components/Settings/TopClicksList.vue";
import TopReferrersList from "@/components/Settings/TopReferrersList.vue";
import TrackingDisabledNotice from "@/components/Settings/TrackingDisabledNotice.vue";
import { useAnalytics } from "@/composables/useAnalytics";
import usePageStore from "@/stores/pageStore";

const pageStore = usePageStore();
const {
	range,
	route,
	customDateRange,
	trackingEnabled,
	analyticsData,
	chartConfigWithEvents,
	processedAnalyticsData,
	analytics,
	ctr,
	ctrData,
} = useAnalytics({
	apiUrl: "builder.api.get_page_analytics",
	ctrApiUrl: "builder.api.get_page_ctr",
	initialRange: "last_30_days",
	initialRouteFilterType: "exact",
	initialRoute: pageStore.getResolvedPageURL(false),
});
</script>
