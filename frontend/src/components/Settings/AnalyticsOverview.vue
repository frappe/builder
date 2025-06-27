<template>
	<div class="my-5 flex flex-col gap-4 text-ink-gray-9">
		<div class="flex items-center justify-between gap-4">
			<span class="text-lg font-medium">Overview</span>
			<div class="flex gap-2">
				<slot name="filters"></slot>
			</div>
		</div>
		<div class="flex gap-8">
			<div class="flex flex-col gap-2">
				<span class="text-3xl">{{ loading ? "-" : shortenNumber(data.total_unique_views) }}</span>
				<span class="text-sm text-ink-gray-7">Unique Visitors</span>
			</div>
			<div class="flex flex-col gap-2">
				<span class="text-3xl">{{ loading ? "-" : shortenNumber(data.total_views) }}</span>
				<span class="text-sm text-ink-gray-7">Total Pageviews</span>
			</div>
		</div>
	</div>
	<div class="mx-[-16px]">
		<div v-if="loading" class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
			Loading...
		</div>
		<AxisChart v-else-if="data.data && data.data.length" :config="chartConfig" />
	</div>
</template>

<script setup lang="ts">
import type { AnalyticsResponse } from "@/composables/useAnalytics";
import { shortenNumber } from "@/utils/helpers";
import { AxisChart } from "frappe-ui";

defineProps<{
	data: AnalyticsResponse;
	chartConfig: any;
	loading: boolean;
}>();
</script>
