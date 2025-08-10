import { shortenNumber } from "@/utils/helpers";
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

export interface CustomDateRange {
	from_date: string;
	to_date: string;
}

export type RouteFilterType = "exact" | "wildcard";

export interface RouteFilter {
	value: string;
	type: RouteFilterType;
}

export function useAnalytics({
	apiUrl,
	initialRange = "last_30_days",
	initialInterval = "daily",
	initialRoute = "",
	initialRouteFilterType = "wildcard",
	extraParams = {},
	onSuccess,
}: {
	apiUrl: string;
	initialRange?: string;
	initialInterval?: string;
	initialRoute?: string;
	initialRouteFilterType?: RouteFilterType;
	extraParams?: Record<string, any>;
	onSuccess?: (res: AnalyticsResponse) => void;
}) {
	const range = ref(initialRange);
	const interval = ref(initialInterval);
	const route = ref(initialRoute);
	const routeFilterType = ref<RouteFilterType>(initialRouteFilterType);
	const customDateRange = ref<string>("");
	const analyticsData = ref<AnalyticsResponse>({
		total_unique_views: 0,
		total_views: 0,
		data: [],
		top_pages: [],
		top_referrers: [],
	});

	const themeColors = {
		textColor: "var(--ink-gray-5)",
		axisLineColor: "var(--ink-gray-4)",
		gridLineColor: "var(--outline-gray-1)",
		backgroundColor: "transparent",
		tooltipBg: "var(--surface-white)",
		tooltipBorder: "var(--outline-gray-1)",
		tooltipText: "var(--ink-gray-7)",
	};

	const getAxisStyle = () => ({
		axisLine: { lineStyle: { color: themeColors.axisLineColor } },
		axisTick: { lineStyle: { color: themeColors.axisLineColor } },
		axisLabel: { color: themeColors.textColor },
		splitLine: { lineStyle: { color: themeColors.gridLineColor } },
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
			{
				name: "total_page_views",
				type: "area",
				axis: "y2",
			},
			{
				name: "unique_page_views",
				type: "area",
				axis: "y2",
			},
		],
		echartOptions: {
			backgroundColor: themeColors.backgroundColor,
			textStyle: { color: themeColors.textColor },
			grid: { borderColor: themeColors.gridLineColor },
			xAxis: getAxisStyle(),
			yAxis: [getAxisStyle(), getAxisStyle()],
			tooltip: {
				backgroundColor: themeColors.tooltipBg,
				borderColor: themeColors.tooltipBorder,
				textStyle: { color: themeColors.tooltipText },
			},
			legend: { textStyle: { color: themeColors.textColor } },
		},
	}));

	const chartConfigWithEvents = computed(() => ({
		...chartConfig.value,
		events: {
			click: (params: any) => {
				if (interval.value !== "hourly") {
					drillDown({ interval: params.name });
				}
			},
		},
	}));

	const processedAnalyticsData = computed(() => {
		return {
			top_referrers: analyticsData.value.top_referrers?.map((referrer) => ({
				...referrer,
				count: shortenNumber(referrer.count),
			})),
			top_pages: analyticsData.value.top_pages?.map((page) => ({
				...page,
				view_count: shortenNumber(page.view_count),
			})),
		};
	});

	const onPageRowClick = (row: { route: string }) => {
		window.open(`/${row.route}`, "_blank");
	};

	const getDateRangeFromPreset = (preset: string): CustomDateRange => {
		const toDate = new Date();
		const fromDate = new Date();

		switch (preset) {
			case "today":
				fromDate.setHours(0, 0, 0, 0);
				toDate.setHours(23, 59, 59, 999);
				break;
			case "this_week":
				const dayOfWeek = toDate.getDay();
				fromDate.setDate(toDate.getDate() - dayOfWeek);
				fromDate.setHours(0, 0, 0, 0);
				toDate.setHours(23, 59, 59, 999);
				break;
			case "last_7_days":
				fromDate.setDate(toDate.getDate() - 7);
				break;
			case "last_30_days":
				fromDate.setDate(toDate.getDate() - 30);
				break;
			case "last_90_days":
				fromDate.setDate(toDate.getDate() - 90);
				break;
			case "last_180_days":
				fromDate.setDate(toDate.getDate() - 180);
				break;
			case "this_year":
				fromDate.setFullYear(toDate.getFullYear(), 0, 1);
				fromDate.setHours(0, 0, 0, 0);
				toDate.setHours(23, 59, 59, 999);
				break;
			default:
				// Default to last 30 days
				fromDate.setDate(toDate.getDate() - 30);
		}

		return {
			from_date: fromDate.toISOString().split("T")[0],
			to_date: toDate.toISOString().split("T")[0],
		};
	};

	const getDefaultInterval = (preset: string, customRange?: CustomDateRange): string => {
		if (customRange) {
			return getIntervalFromDateRange(customRange.from_date, customRange.to_date);
		}

		const intervalMap: Record<string, string> = {
			today: "hourly",
			this_week: "daily",
			last_7_days: "daily",
			last_30_days: "daily",
			last_90_days: "weekly",
			last_180_days: "weekly",
			this_year: "monthly",
		};
		return intervalMap[preset] || "daily";
	};

	const getIntervalFromDateRange = (fromDate: string, toDate: string): string => {
		const from = new Date(fromDate);
		const to = new Date(toDate);
		const diffInMs = to.getTime() - from.getTime();
		const diffInDays = Math.ceil(diffInMs / (1000 * 60 * 60 * 24));

		if (diffInDays <= 1) {
			return "hourly";
		} else if (diffInDays <= 31) {
			return "daily";
		} else {
			return "monthly";
		}
	};

	const getDefaultDateRange = (): CustomDateRange => {
		return getDateRangeFromPreset("last_30_days");
	};

	const setCustomDateRange = (fromDate: string, toDate: string) => {
		customDateRange.value = `${fromDate},${toDate}`;
		range.value = "custom";
	};

	const clearCustomDateRange = () => {
		customDateRange.value = "";
		if (range.value === "custom") {
			range.value = "last_30_days";
		}
	};

	const setCustomRangeWithDefault = () => {
		if (!customDateRange.value) {
			const defaultRange = getDefaultDateRange();
			setCustomDateRange(defaultRange.from_date, defaultRange.to_date);
		} else {
			range.value = "custom";
		}
	};

	const drillDown = (dataPoint: { interval: string; [key: string]: any }) => {
		const currentInterval =
			interval.value ||
			getIntervalFromDateRange(
				range.value === "custom" && customDateRange.value
					? parseCustomDateRange(customDateRange.value)?.from_date || ""
					: getDateRangeFromPreset(range.value).from_date,
				range.value === "custom" && customDateRange.value
					? parseCustomDateRange(customDateRange.value)?.to_date || ""
					: getDateRangeFromPreset(range.value).to_date,
			);

		const clickedDate = new Date(dataPoint.interval);

		let newFromDate: string;
		let newToDate: string;
		let newInterval: string;

		if (currentInterval === "monthly") {
			newFromDate = new Date(clickedDate.getFullYear(), clickedDate.getMonth(), 1)
				.toISOString()
				.split("T")[0];
			newToDate = new Date(clickedDate.getFullYear(), clickedDate.getMonth() + 1, 0)
				.toISOString()
				.split("T")[0];
			newInterval = "daily";
		} else if (currentInterval === "daily") {
			newFromDate = clickedDate.toISOString().split("T")[0];
			newToDate = clickedDate.toISOString().split("T")[0];
			newInterval = "hourly";
		} else {
			return;
		}

		setCustomDateRange(newFromDate, newToDate);
		interval.value = newInterval;
	};

	const parseCustomDateRange = (dateRangeString: string): CustomDateRange | null => {
		if (!dateRangeString || !dateRangeString.includes(",")) {
			return null;
		}
		const [from_date, to_date] = dateRangeString.split(",");
		return { from_date: from_date.trim(), to_date: to_date.trim() };
	};

	const setRouteFilter = (routeValue: string, filterType: RouteFilterType = "wildcard") => {
		route.value = routeValue;
		routeFilterType.value = filterType;
	};

	const getFormattedRoute = () => {
		if (!route.value) return "";

		if (routeFilterType.value === "exact") {
			return route.value;
		} else {
			return route.value;
		}
	};

	const getParams = () => {
		const params: Record<string, any> = {
			...extraParams,
		};

		let dateRange: CustomDateRange;

		if (range.value === "custom" && customDateRange.value) {
			const parsedRange = parseCustomDateRange(customDateRange.value);
			if (parsedRange) {
				dateRange = parsedRange;
			} else {
				dateRange = getDefaultDateRange();
			}
		} else {
			dateRange = getDateRangeFromPreset(range.value);
		}

		params.from_date = dateRange.from_date;
		params.to_date = dateRange.to_date;

		if (range.value === "custom" && customDateRange.value) {
			params.interval = getIntervalFromDateRange(dateRange.from_date, dateRange.to_date);
		} else {
			params.interval = getDefaultInterval(range.value, dateRange);
		}

		if (interval.value) {
			params.interval = interval.value;
		}

		const formattedRoute = getFormattedRoute();
		if (formattedRoute) {
			params.route = formattedRoute;
			params.route_filter_type = routeFilterType.value;
		}

		return params;
	};

	const analytics = createResource({
		method: "POST",
		url: apiUrl,
		params: getParams(),
		auto: true,
		onSuccess(res: AnalyticsResponse) {
			analyticsData.value = res;
			onSuccess?.(res);
		},
	});

	watch(
		[range, interval, route, routeFilterType, customDateRange],
		(newValues, oldValues) => {
			if (newValues[0] !== oldValues?.[0] && newValues[0] !== "custom") {
				interval.value = "";
			}
			analytics.submit(getParams());
		},
		{ deep: true },
	);

	return {
		range,
		interval,
		route,
		routeFilterType,
		customDateRange,
		analyticsData,
		chartConfig,
		chartConfigWithEvents,
		processedAnalyticsData,
		analytics,
		setCustomDateRange,
		clearCustomDateRange,
		setCustomRangeWithDefault,
		setRouteFilter,
		getFormattedRoute,
		parseCustomDateRange,
		getDefaultDateRange,
		getDateRangeFromPreset,
		getDefaultInterval,
		getIntervalFromDateRange,
		drillDown,
		onPageRowClick,
	};
}
