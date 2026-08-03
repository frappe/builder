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
				label: "视频 URL",
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
				label: "封面",
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
				label: "控件",
				options: [
					{ label: "显示", value: "true" },
					{ label: "隐藏", value: "false" },
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
				label: "自动播放",
				options: [
					{ label: "是", value: "true" },
					{ label: "否", value: "false" },
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
				label: "静音",
				options: [
					{ label: "是", value: "true" },
					{ label: "否", value: "false" },
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
				label: "循环",
				options: [
					{ label: "是", value: "true" },
					{ label: "否", value: "false" },
				],
				getModelValue: () => (blockController.getAttribute("loop") === "" ? "true" : "false"),
				setModelValue: () => blockController.toggleAttribute("loop"),
			};
		},
		searchKeyWords: "Loop",
	},
];

export default {
	name: "视频选项",
	properties: videoOptionsSectionProperties,
	condition: () => blockController.isVideo(),
};
