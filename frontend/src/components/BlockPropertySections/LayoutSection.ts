import BlockFlexLayoutHandler from "@/components/BlockFlexLayoutHandler.vue";
import BlockGridLayoutHandler from "@/components/BlockGridLayoutHandler.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";
import PropertyControl from "../Controls/PropertyControl.vue";

const layoutSectionProperties = [
	{
		component: PropertyControl,
		condition: () => !blockController.isText(),
		getProps: () => {
			return {
				styleProperty: "display",
				component: OptionToggle,
				label: "Type",
				enableStates: false,
				options: [
					{
						label: "Stack",
						value: "flex",
					},
					{
						label: "Grid",
						value: "grid",
					},
				],
			};
		},
		searchKeyWords: "Layout, Display, Flex, Grid, Flexbox, Flex Box, FlexBox",
		events: {
			"update:modelValue": (val: StyleValue) => {
				blockController.setStyle("display", val);
				if (val === "grid") {
					if (!blockController.getStyle("gridTemplateColumns")) {
						blockController.setStyle("gridTemplateColumns", "repeat(2, minmax(200px, 1fr))");
					}
					if (!blockController.getStyle("gap")) {
						blockController.setStyle("gap", "10px");
					}
					if (blockController.getStyle("height")) {
						if (blockController.getSelectedBlocks()[0].hasChildren()) {
							blockController.setStyle("height", null);
						}
					}
				}
			},
		},
	},
	{
		component: BlockGridLayoutHandler,
		getProps: () => {},
		searchKeyWords:
			"Layout, Grid, GridTemplate, Grid Template, GridGap, Grid Gap, GridRow, Grid Row, GridColumn, Grid Column",
	},
	{
		component: BlockFlexLayoutHandler,
		getProps: () => {},
		searchKeyWords:
			"Layout, Flex, Flexbox, Flex Box, FlexBox, Justify, Space Between, Flex Grow, Flex Shrink, Flex Basis, Align Items, Align Content, Align Self, Flex Direction, Flex Wrap, Flex Flow, Flex Grow, Flex Shrink, Flex Basis, Gap",
	},
];

export default {
	name: "Layout",
	properties: layoutSectionProperties,
	condition: () => !blockController.multipleBlocksSelected(),
};
