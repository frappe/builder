import DimensionInput from "@/components/DimensionInput.vue";

const dimensionSectionProperties = [
	{
		component: DimensionInput,
		searchKeyWords: "Width",
		getProps: () => {
			return {
				label: "Width",
				property: "width",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Min, Width, MinWidth, Min Width",
		getProps: () => {
			return {
				label: "Min Width",
				property: "minWidth",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Max, Width, MaxWidth, Max Width",
		getProps: () => {
			return {
				label: "Max Width",
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
				label: "Height",
				property: "height",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Min, Height, MinHeight, Min Height",
		getProps: () => {
			return {
				label: "Min Height",
				property: "minHeight",
			};
		},
	},
	{
		component: DimensionInput,
		searchKeyWords: "Max, Height, MaxHeight, Max Height",
		getProps: () => {
			return {
				label: "Max Height",
				property: "maxHeight",
			};
		},
	},
];

export default {
	name: "Dimension",
	properties: dimensionSectionProperties,
};
