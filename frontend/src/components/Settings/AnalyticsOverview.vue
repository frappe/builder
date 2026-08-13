<template>
	<div class="my-5 flex flex-col gap-4 text-ink-gray-9">
		<div class="flex items-center justify-between gap-4">
			<span class="text-lg-medium">{{ __("Overview") }}</span>
			<div class="flex gap-2">
				<slot name="filters"></slot>
			</div>
		</div>
		<div class="flex gap-8">
			<div class="flex flex-col gap-2">
				<span class="text-4xl">{{ loading ? "-" : shortenNumber(data.total_unique_views) }}</span>
				<span class="text-sm text-ink-gray-7">{{ __("Unique Visitors") }}</span>
			</div>
			<div class="flex flex-col gap-2">
				<span class="text-4xl">{{ loading ? "-" : shortenNumber(data.total_views) }}</span>
				<span class="text-sm text-ink-gray-7">{{ __("Total Pageviews") }}</span>
			</div>
			<div v-if="ctr !== undefined" class="flex flex-col gap-2">
				<span class="text-4xl">{{ loading ? "-" : `${ctr}%` }}</span>
				<span class="text-sm text-ink-gray-7">{{ __("Click-through Rate") }}</span>
			</div>
		</div>
	</div>
	<div class="mx-[-16px]">
		<div v-if="loading" class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
			{{ __("Loading...") }}
		</div>
		<AxisChart
			v-else-if="data.data && data.data.length"
			class="!h-[250px] !min-h-[200px]"
			:config="chartConfigData"
			:events="chartEvents" />
		<AnalyticsEmptyState
			v-else
			:title="__('No views in this period')"
			:hint="__('Pick a wider date range, or share your page to start collecting data.')" />
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import AnalyticsEmptyState from "@/components/Settings/AnalyticsEmptyState.vue";
import type { AnalyticsResponse } from "@/composables/useAnalytics";
import { shortenNumber } from "@/utils/helpers";
import { AxisChart } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	data: AnalyticsResponse;
	chartConfig: any;
	loading: boolean;
	ctr?: number;
}>();

const chartConfigData = computed(() => {
	const { events, ...config } = props.chartConfig;
	return config;
});

const chartEvents = computed(() => {
	return props.chartConfig.events;
});
</script>
