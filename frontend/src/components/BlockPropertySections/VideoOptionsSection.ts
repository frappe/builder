import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import blockController from "@/utils/blockController";

const videoOptionsSectionProperties = [
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				component: InlineInput,
				propertyKey: "src",
				label: "Video URL",
				allowDynamicValue: true,
				dynamicValueFilterOptions: {
					excludeOwnProps: true,
					excludeOwnBlockData: true,
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
				label: "Poster",
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
				label: "Controls",
				options: [
					{ label: "Show", value: "true" },
					{ label: "Hide", value: "false" },
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
				label: "Autoplay",
				options: [
					{ label: "Yes", value: "true" },
					{ label: "No", value: "false" },
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
				label: "Muted",
				options: [
					{ label: "Yes", value: "true" },
					{ label: "No", value: "false" },
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
				label: "Loop",
				options: [
					{ label: "Yes", value: "true" },
					{ label: "No", value: "false" },
				],
				getModelValue: () => (blockController.getAttribute("loop") === "" ? "true" : "false"),
				setModelValue: () => blockController.toggleAttribute("loop"),
			};
		},
		searchKeyWords: "Loop",
	},
];

export default {
	name: "Video Options",
	properties: videoOptionsSectionProperties,
	condition: () => blockController.isVideo(),
};
