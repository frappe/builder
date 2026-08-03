import DimensionInput from "@/components/DimensionInput.vue";

const dimensionSectionProperties = [
	{
		component: DimensionInput,
		searchKeyWords: "Width",
		getProps: () => {
			return {
				label: "宽度",
				property: "width",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Min, Width, MinWidth, Min Width",
		getProps: () => {
			return {
				label: "最小宽度",
				property: "minWidth",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Max, Width, MaxWidth, Max Width",
		getProps: () => {
			return {
				label: "最大宽度",
				property: "maxWidth",
			};
		},
	},
	{
		component: "hr",
		getProps: () => {
			return {
				class: "border-outline-gray-1",
			};
		},
		searchKeyWords: "",
	},
	{
		component: DimensionInput,
		searchKeyWords: "Height",
		getProps: () => {
			return {
				label: "高度",
				property: "height",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Min, Height, MinHeight, Min Height",
		getProps: () => {
			return {
				label: "最小高度",
				property: "minHeight",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Max, Height, MaxHeight, Max Height",
		getProps: () => {
			return {
				label: "最大高度",
				property: "maxHeight",
			};
		},
	},
];

export default {
	name: "尺寸",
	properties: dimensionSectionProperties,
};
