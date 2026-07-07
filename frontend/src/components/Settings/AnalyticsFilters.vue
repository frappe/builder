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
		<div class="w-32">
			<Select size="sm" v-model="modelRange" :options="rangeOptions" />
		</div>
		<DateRangePicker
			v-if="modelRange === 'custom'"
			v-model="customDateRangeValue"
			placeholder="Select date range"
			format="MMM D, YYYY"
			size="sm"
			class="!w-56" />
	</div>
</template>

<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import { webPages } from "@/data/webPage";
import { BuilderPage } from "@/types/doctypes";
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
// DateRangePicker works with a [from, to] array; we persist it as a "from,to" string.
const customDateRangeValue = computed<string[]>({
	get: () => (props.customDateRange ? props.customDateRange.split(",") : []),
	set: (val) => emit("update:customDateRange", (val ?? []).join(",")),
});

const getRouteOptions = async (query: string) => {
	if (!webPages.data?.length) {
		await webPages.fetch();
	}

	const queryLower = query?.toLowerCase() || "";

	return (webPages.data ?? [])
		.filter((page: BuilderPage) => page.route && !page.dynamic_route)
		.map((page: BuilderPage) => ({ value: page.route as string, label: page.route as string }))
		.filter(
			(option: { value: string; label: string }) =>
				!queryLower || option.label.toLowerCase().includes(queryLower),
		);
};
</script>
