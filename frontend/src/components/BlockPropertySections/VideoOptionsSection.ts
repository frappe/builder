import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

const videoOptionsSectionProperties = [
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: InlineInput,
				propertyKey: "src",
				label: __("Video URL"),
				allowDynamicValue: true,
				dynamicValueFilterOptions: {
					excludeOwnProps: true,
				},
			};
		},
		searchKeyWords: "Source, URL, Link, Video URL, Video Link",
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: ImageUploadInput,
				propertyKey: "poster",
				label: __("Poster"),
			};
		},
		searchKeyWords: "Poster, Image, Thumbnail, Preview",
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: OptionToggle,
				propertyKey: "controls",
				label: __("Controls"),
				options: [
					{ label: __("Show"), value: "true" },
					{ label: __("Hide"), value: "false" },
				],
				getModelValue: () => (blockController.getAttribute("controls") === "" ? "true" : "false"),
				setModelValue: () => blockController.toggleAttribute("controls"),
			};
		},
		searchKeyWords: "Controls, volume, play, pause, stop, mute, unmute, fullscreen, full screen",
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: OptionToggle,
				propertyKey: "autoplay",
				label: __("Autoplay"),
				options: [
					{ label: __("Yes"), value: "true" },
					{ label: __("No"), value: "false" },
				],
				getModelValue: () => (blockController.getAttribute("autoplay") === "" ? "true" : "false"),
				setModelValue: () => blockController.toggleAttribute("autoplay"),
			};
		},
		searchKeyWords: "Autoplay, Auto Play",
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: OptionToggle,
				propertyKey: "muted",
				label: __("Muted"),
				options: [
					{ label: __("Yes"), value: "true" },
					{ label: __("No"), value: "false" },
				],
				getModelValue: () => (blockController.getAttribute("muted") === "" ? "true" : "false"),
				setModelValue: () => blockController.toggleAttribute("muted"),
			};
		},
		searchKeyWords: "Muted",
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: OptionToggle,
				propertyKey: "loop",
				label: __("Loop"),
				options: [
					{ label: __("Yes"), value: "true" },
					{ label: __("No"), value: "false" },
				],
				getModelValue: () => (blockController.getAttribute("loop") === "" ? "true" : "false"),
				setModelValue: () => blockController.toggleAttribute("loop"),
			};
		},
		searchKeyWords: "Loop",
	},
];

export default {
	name: __("Video Options"),
	properties: videoOptionsSectionProperties,
	condition: () => blockController.isVideo(),
};
