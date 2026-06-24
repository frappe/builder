<template>
	<div class="no-scrollbar h-full overflow-y-auto overflow-x-hidden pr-1">
		<TrackingDisabledNotice v-if="websiteSettings.doc && !trackingEnabled" />
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
			<div class="mt-8">
				<h3 class="text-xl-medium mb-4 text-ink-gray-7">Top Clicks</h3>
				<div
					v-if="ctr?.loading"
					class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
					Loading...
				</div>
				<ListView
					v-else-if="ctrRows.length"
					class="!w-auto"
					:columns="[
						{ label: 'Target', key: 'label', width: '50%' },
						{ label: 'Clicks', key: 'clicks', align: 'right' },
						{ label: 'CTR', key: 'ctr_label', align: 'right' },
					]"
					:options="{ selectable: false, emptyState: {}, showTooltip: false }"
					:rows="ctrRows"
					row-key="label" />
				<AnalyticsEmptyState
					v-else
					title="No clicks tracked yet"
					hint="Clicks on links and buttons will appear here." />
			</div>
			<div class="mt-8">
				<h3 class="text-xl-medium mb-4 text-ink-gray-7">Top Referrers</h3>
				<div
					v-if="analytics.loading"
					class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
					Loading...
				</div>
				<ListView
					v-else-if="processedAnalyticsData.top_referrers?.length"
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
				<AnalyticsEmptyState v-else title="No referrers yet" />
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import AnalyticsEmptyState from "@/components/Settings/AnalyticsEmptyState.vue";
import AnalyticsFilters from "@/components/Settings/AnalyticsFilters.vue";
import AnalyticsOverview from "@/components/Settings/AnalyticsOverview.vue";
import TrackingDisabledNotice from "@/components/Settings/TrackingDisabledNotice.vue";
import { useAnalytics } from "@/composables/useAnalytics";
import { websiteSettings } from "@/data/websiteSettings";
import usePageStore from "@/stores/pageStore";
import { ListView } from "frappe-ui";
import { computed, h } from "vue";

const pageStore = usePageStore();
const trackingEnabled = computed(() => Boolean(websiteSettings.doc?.enable_view_tracking));
const {
	range,
	interval,
	route,
	customDateRange,
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

const ctrRows = computed(() =>
	ctrData.value.elements.map((el) => ({
		...el,
		ctr_label: `${el.ctr}%`,
	})),
);
</script>
