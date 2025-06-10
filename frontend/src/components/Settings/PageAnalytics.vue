<template>
	<div class="my-5 flex flex-col gap-4 text-ink-gray-9">
		<div class="flex justify-between">
			<span class="text-lg font-medium">Overview</span>
			<Select
				size="sm"
				:options="[
					{
						label: 'Today',
						value: 'today',
					},
					{
						label: 'Last 30 Days',
						value: 'last-30-days',
					},
					{
						label: 'Last 7 Days',
						value: 'last-7-days',
					},
					{
						label: 'This Year',
						value: 'this-year',
					},
				]" />
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
	<div class="mx-[-16px]" v-if="analyticsData.data.length">
		<AxisChart :config="chartConfig" />
	</div>
</template>
<script setup lang="ts">
import usePageStore from "@/stores/pageStore";
import { AxisChart, Select, createResource } from "frappe-ui";
import { computed, ref } from "vue";

const pageStore = usePageStore();
const analyticsData = ref({
	total_unique_views: 0,
	total_views: 0,
	data: [],
});

const chartConfig = computed(() => ({
	data: analyticsData.value.data,
	title: "",
	xAxis: {
		key: "interval",
		type: "value",
		title: "Month",
		timeGrain: "month",
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

const analytics = createResource({
	method: "POST",
	url: "builder.api.get_page_analytics",
	params: {
		route: pageStore.activePage?.route,
		interval: "month",
	},
	auto: true,
});

analytics.promise
	.then((res) => {
		console.log("Analytics Data:", res);
		analyticsData.value = res;
	})
	.catch(console.error);
</script>
