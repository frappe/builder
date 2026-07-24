import BlockFlexLayoutHandler from "@/components/BlockFlexLayoutHandler.vue";
import BlockGridLayoutHandler from "@/components/BlockGridLayoutHandler.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";
import StylePropertyControl from "../Controls/StylePropertyControl.vue";

const layoutSectionProperties = [
	{
		component: StylePropertyControl,
		condition: () => !blockController.isText(),
		getProps: () => {
			return {
				propertyKey: "display",
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
		condition: () => blockController.isGrid() || Boolean(blockController.getParentBlock()?.isGrid()),
		getProps: () => {},
		ownedStyleProperties: [
			"column-gap",
			"gap",
			"grid-auto-columns",
			"grid-auto-flow",
			"grid-auto-rows",
			"grid-column",
			"grid-column-end",
			"grid-column-start",
			"grid-row",
			"grid-row-end",
			"grid-row-start",
			"grid-template",
			"grid-template-areas",
			"grid-template-columns",
			"grid-template-rows",
			"justify-items",
			"place-content",
			"place-items",
			"place-self",
			"row-gap",
		],
		searchKeyWords:
			"Layout, Grid, GridTemplate, Grid Template, GridGap, Grid Gap, GridRow, Grid Row, GridColumn, Grid Column",
	},
	{
		component: BlockFlexLayoutHandler,
		condition: () => blockController.isFlex() || Boolean(blockController.getParentBlock()?.isFlex()),
		getProps: () => {},
		ownedStyleProperties: [
			"align-content",
			"align-items",
			"align-self",
			"flex",
			"flex-basis",
			"flex-direction",
			"flex-flow",
			"flex-grow",
			"flex-shrink",
			"flex-wrap",
			"gap",
			"justify-content",
			"justify-self",
			"order",
		],
		searchKeyWords:
			"Layout, Flex, Flexbox, Flex Box, FlexBox, Justify, Space Between, Flex Grow, Flex Shrink, Flex Basis, Align Items, Align Content, Align Self, Flex Direction, Flex Wrap, Flex Flow, Flex Grow, Flex Shrink, Flex Basis, Gap, Order",
	},
];

export default {
	name: "Layout",
	properties: layoutSectionProperties,
	condition: () => !blockController.multipleBlocksSelected() && !blockController.isHTML(),
};
