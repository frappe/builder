<template>
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
</template>

<script setup lang="ts">
import AnalyticsFilters from "@/components/Settings/AnalyticsFilters.vue";
import AnalyticsOverview from "@/components/Settings/AnalyticsOverview.vue";
import { useAnalytics } from "@/composables/useAnalytics";
import usePageStore from "@/stores/pageStore";

const pageStore = usePageStore();
const { range, interval, analyticsData, chartConfig, analytics } = useAnalytics({
	apiUrl: "builder.api.get_page_analytics",
	initialRange: "last_30_days",
	initialInterval: "weekly",
	extraParams: { route: pageStore.activePage?.route },
});
</script>
