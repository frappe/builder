<template>
	<div class="no-scrollbar h-full overflow-y-auto">
		<div class="my-5 flex flex-col gap-4 text-ink-gray-9">
			<div class="flex items-center justify-between gap-4">
				<span class="text-lg font-medium">Overview</span>
				<div class="flex gap-2">
					<Select
						size="sm"
						v-model="interval"
						:options="[
							{
								label: 'Hourly',
								value: 'hourly',
							},
							{
								label: 'Daily',
								value: 'daily',
							},
							{
								label: 'Weekly',
								value: 'weekly',
							},
							{
								label: 'Monthly',
								value: 'monthly',
							},
						]" />
					<Select
						size="sm"
						v-model="range"
						:options="[
							{
								label: 'Today',
								value: 'today',
							},
							{
								label: 'Last 7 Days',
								value: 'last_7_days',
							},
							{
								label: 'Last 30 Days',
								value: 'last_30_days',
							},
							{
								label: 'This Year',
								value: 'this_year',
							},
						]" />
				</div>
			</div>
			<div class="flex gap-8">
				<div class="flex flex-col gap-2">
					<span class="text-3xl">{{ analyticsData.total_unique_views }}</span>
					<span class="text-sm text-ink-gray-7">Unique Visitors</span>
				</div>
				<div class="flex flex-col gap-2">
					<span class="text-3xl">{{ analyticsData.total_views }}</span>
					<span class="text-sm text-ink-gray-7">Total Pageviews</span>
				</div>
			</div>
		</div>
		<div v-if="analyticsData.data.length">
			<AxisChart :config="chartConfig" />
		</div>

		<div class="mt-8">
			<h3 class="mb-4 text-lg font-medium">Top Pages</h3>
			<ListView
				:columns="[
					{
						label: 'Route',
						key: 'route',
						width: '70%',
					},
					{
						label: 'Total Views',
						key: 'view_count',
					},
					{
						label: 'Unique Views',
						key: 'unique_view_count',
					},
				]"
				:options="{
					selectable: false,
					emptyState: {},
				}"
				:rows="analyticsData.top_pages"
				row-key="route" />
		</div>
	</div>
</template>

<script setup lang="ts">
import usePageStore from "@/stores/pageStore";
import { AxisChart, createResource, ListView, Select } from "frappe-ui";
import { computed, ref, watch } from "vue";

const pageStore = usePageStore();
const range = ref("last_30_days");
const interval = ref("weekly");
const analyticsData = ref<AnalyticsResponse>({
	total_unique_views: 0,
	total_views: 0,
	data: [],
	top_pages: [],
});

const chartConfig = computed(() => ({
	data: analyticsData.value.data,
	title: "",
	xAxis: {
		key: "interval",
		type: "category",
	},
	yAxis: {
		title: "Timeline",
	},
	y2Axis: {
		title: "Total Views",
	},
	series: [
		{ name: "total_page_views", type: "area", axis: "y2" },
		{ name: "unique_page_views", type: "area", axis: "y2" },
	],
}));

interface AnalyticsResponse {
	total_unique_views: number;
	total_views: number;
	data: [];
	top_pages: Array<{
		route: string;
		view_count: number;
		unique_view_count: number;
	}>;
}

const analytics = createResource({
	method: "POST",
	url: "builder.api.get_overall_analytics",
	params: {
		date_range: range.value,
		interval: interval.value,
	},
	auto: true,
	onSuccess(res: AnalyticsResponse) {
		analyticsData.value = res;
		console.log("Analytics Data:", res);
	},
});

watch([range, interval], () => {
	analytics.submit({
		route: pageStore.activePage?.route,
		date_range: range.value,
		interval: interval.value,
	});
});
</script>
