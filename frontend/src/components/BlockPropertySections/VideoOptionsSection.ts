import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";

const videoOptionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Video URL",
				modelValue: blockController.getAttribute("src"),
			};
		},
		searchKeyWords: "Video, URL, Src",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("src", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Poster",
				modelValue: blockController.getAttribute("poster"),
			};
		},
		searchKeyWords: "Poster",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("poster", val),
		},
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Controls",
				options: [
					{
						label: "Show",
						value: "true",
					},
					{
						label: "Hide",
						value: "false",
					},
				],
				modelValue: blockController.getAttribute("controls") === "" ? "true" : "false",
			};
		},
		searchKeyWords: "Controls, volume, play, pause, stop, mute, unmute, fullscreen, full screen",
		events: {
			"update:modelValue": (val: boolean) => blockController.toggleAttribute("controls"),
		},
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Autoplay",
				options: [
					{
						label: "Yes",
						value: "true",
					},
					{
						label: "No",
						value: "false",
					},
				],
				modelValue: blockController.getAttribute("autoplay") === "" ? "true" : "false",
			};
		},
		searchKeyWords: "Autoplay, Auto Play",
		events: {
			"update:modelValue": (val: boolean) => blockController.toggleAttribute("autoplay"),
		},
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Muted",
				options: [
					{
						label: "Yes",
						value: "true",
					},
					{
						label: "No",
						value: "false",
					},
				],
				modelValue: blockController.getAttribute("muted") === "" ? "true" : "false",
			};
		},
		searchKeyWords: "Muted",
		events: {
			"update:modelValue": (val: boolean) => blockController.toggleAttribute("muted"),
		},
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Loop",
				options: [
					{
						label: "Yes",
						value: "true",
					},
					{
						label: "No",
						value: "false",
					},
				],
				modelValue: blockController.getAttribute("loop") === "" ? "true" : "false",
			};
		},
		searchKeyWords: "Loop",
		events: {
			"update:modelValue": (val: boolean) => blockController.toggleAttribute("loop"),
		},
	},
];

export default {
	name: "Video Options",
	properties: videoOptionsSectionProperties,
	condition: () => blockController.isVideo(),
};
