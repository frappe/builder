import { createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";

export interface AnalyticsResponse {
	total_unique_views: number;
	total_views: number;
	data: any[];
	top_pages?: Array<{
		route: string;
		view_count: number;
		unique_view_count: number;
	}>;
	top_referrers?: Array<{
		domain: string;
		count: number;
	}>;
}

export function useAnalytics({
	apiUrl,
	initialRange = "last_30_days",
	initialInterval = "weekly",
	extraParams = {},
	onSuccess,
}: {
	apiUrl: string;
	initialRange?: string;
	initialInterval?: string;
	extraParams?: Record<string, any>;
	onSuccess?: (res: AnalyticsResponse) => void;
}) {
	const range = ref(initialRange);
	const interval = ref(initialInterval);
	const analyticsData = ref<AnalyticsResponse>({
		total_unique_views: 0,
		total_views: 0,
		data: [],
		top_pages: [],
		top_referrers: [],
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

	const analytics = createResource({
		method: "POST",
		url: apiUrl,
		params: {
			...extraParams,
			date_range: range.value,
			interval: interval.value,
		},
		auto: true,
		onSuccess(res: AnalyticsResponse) {
			analyticsData.value = res;
			onSuccess?.(res);
		},
	});

	watch([range, interval], () => {
		analytics.submit({
			...extraParams,
			date_range: range.value,
			interval: interval.value,
		});
	});

	return {
		range,
		interval,
		analyticsData,
		chartConfig,
		analytics,
	};
}
