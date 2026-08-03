<template>
	<div class="my-5 flex flex-col gap-4 text-ink-gray-9">
		<div class="flex items-center justify-between gap-4">
			<span class="text-lg-medium">概览</span>
			<div class="flex gap-2">
				<slot name="filters"></slot>
			</div>
		</div>
		<div class="flex gap-8">
			<div class="flex flex-col gap-2">
				<span class="text-4xl">{{ loading ? "-" : shortenNumber(data.total_unique_views) }}</span>
				<span class="text-sm text-ink-gray-7">独立访客</span>
			</div>
			<div class="flex flex-col gap-2">
				<span class="text-4xl">{{ loading ? "-" : shortenNumber(data.total_views) }}</span>
				<span class="text-sm text-ink-gray-7">总浏览量</span>
			</div>
			<div v-if="ctr !== undefined" class="flex flex-col gap-2">
				<span class="text-4xl">{{ loading ? "-" : `${ctr}%` }}</span>
				<span class="text-sm text-ink-gray-7">点击率</span>
			</div>
		</div>
	</div>
	<div class="mx-[-16px] [&>div]:h-[250px] [&>div]:!min-h-[200px]">
		<div v-if="loading" class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
			加载中...
		</div>
		<AxisChart v-else-if="data.data && data.data.length" :config="chartConfigData" :events="chartEvents" />
		<AnalyticsEmptyState
			v-else
			title="该时间段内暂无浏览量"
			hint="选择更宽的时间范围，或分享你的页面以开始收集数据。" />
	</div>
</template>

<script setup lang="ts">
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
