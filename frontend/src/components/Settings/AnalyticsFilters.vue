<template>
	<div class="flex flex-wrap gap-2">
		<Autocomplete
			size="sm"
			placeholder="Filter by route"
			v-model="modelRoute"
			:getOptions="getRouteOptions"
			:allowArbitraryValue="true"
			:showInputAsOption="true"
			class="w-44" />
		<Select size="sm" v-model="modelRange" class="!w-32 pr-6" :options="rangeOptions" />
		<DateRangePicker
			v-if="modelRange === 'custom'"
			v-model="customDateRangeValue"
			placeholder="Select date range"
			:formatter="formatDate"
			size="sm"
			class="!w-56" />
	</div>
</template>

<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import { webPages } from "@/data/webPage";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { DateRangePicker, Select } from "frappe-ui";
import { computed } from "vue";

interface SelectOption {
	label: string;
	value: string;
}

const props = defineProps({
	range: {
		type: String,
		required: true,
	},
	route: {
		type: String,
		default: "",
	},
	customDateRange: {
		type: String,
		default: "",
	},
	rangeOptions: {
		type: Array as () => SelectOption[],
		required: false,
		default: () => [
			{ label: "Today", value: "today" },
			{ label: "Last 7 Days", value: "last_7_days" },
			{ label: "Last 30 Days", value: "last_30_days" },
			{ label: "This Year", value: "this_year" },
			{ label: "Custom", value: "custom" },
		],
	},
});
const emit = defineEmits(["update:range", "update:route", "update:customDateRange"]);

const modelRange = computed({
	get: () => props.range,
	set: (val) => {
		emit("update:range", val);
		// Clear custom date range when switching away from custom
		if (val !== "custom") {
			emit("update:customDateRange", "");
		} else if (val === "custom" && !props.customDateRange) {
			// Set default date range when custom is selected without existing range
			const defaultRange = getDefaultDateRange();
			emit("update:customDateRange", `${defaultRange.from_date},${defaultRange.to_date}`);
		}
	},
});

// Helper function to get default date range (last 30 days)
const getDefaultDateRange = () => {
	const toDate = new Date();
	const fromDate = new Date();
	fromDate.setDate(toDate.getDate() - 30);

	return {
		from_date: fromDate.toISOString().split("T")[0],
		to_date: toDate.toISOString().split("T")[0],
	};
};
const modelRoute = computed({
	get: () => props.route,
	set: (val) => emit("update:route", val),
});
const customDateRangeValue = computed({
	get: () => props.customDateRange,
	set: (val) => emit("update:customDateRange", val),
});

// Format date for display in the date range picker
const formatDate = (date: string) => {
	if (!date) return "";
	const dateObj = new Date(date);
	return dateObj.toLocaleDateString("en-US", {
		year: "numeric",
		month: "short",
		day: "numeric",
	});
};

const getRouteOptions = async (query: string) => {
	if (!webPages.data?.length) {
		await webPages.fetch();
	}

	const queryLower = query?.toLowerCase() || "";

	return webPages.data
		.filter((page: BuilderPage) => page.route && !page.dynamic_route)
		.map((page: BuilderPage) => ({ value: page.route, label: page.route }))
		.filter(
			(option: { value: string; label: string }) =>
				!queryLower || option.label.toLowerCase().includes(queryLower),
		);
};
</script>
