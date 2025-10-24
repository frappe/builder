import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import PropertyControl from "@/components/Controls/PropertyControl.vue";
import ImageUploadInput from "@/components/ImageUploadInput.vue";
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
		component: PropertyControl,
		getProps: () => {
			return {
				component: ImageUploadInput,
				controlType: "attribute",
				styleProperty: "poster",
				label: "Poster",
				imageURL: blockController.getAttribute("poster"),
			};
		},
		events: {
			"update:imageURL": (val: string) => blockController.setAttribute("poster", val),
		},
		searchKeyWords: "Poster, Image, Thumbnail, Preview",
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
