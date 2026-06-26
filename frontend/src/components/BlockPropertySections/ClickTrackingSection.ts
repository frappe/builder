import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";

const clickTrackingSectionProperties = [
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Track Clicks",
				options: [
					{ label: "No", value: false },
					{ label: "Yes", value: true },
				],
				modelValue: blockController.isClickTrackingEnabled(),
			};
		},
		searchKeyWords: "Track, Clicks, Tracking, Analytics, CTR, Click Tracking",
		events: {
			"update:modelValue": (val: boolean) => blockController.toggleClickTracking(val),
		},
	},
];

export default {
	name: "Click Tracking",
	properties: clickTrackingSectionProperties,
};
