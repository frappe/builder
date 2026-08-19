import BlockFlexLayoutHandler from "@/components/BlockFlexLayoutHandler.vue";
import BlockGridLayoutHandler from "@/components/BlockGridLayoutHandler.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";
import { collapseGapShorthand, expandGapShorthand } from "@/utils/cssUtils";
import StylePropertyControl from "../Controls/StylePropertyControl.vue";
import { __ } from "@/translation";

const SPLITS = ["V", "H"];

const gapProps = {
	label: __("Gap"),
	propertyKey: "gap",
	splits: SPLITS,
	toControlValues: (value: unknown) => expandGapShorthand(value),
	toModelValue: (parts: StyleValue[]) => collapseGapShorthand(parts),
	getModelValue: (state: string | null = null) =>
		state
			? String(blockController.getNativeStyle(`${state}:gap`) ?? "")
			: String(blockController.getSpacing("gap", { nativeOnly: true, cascading: false })),
	getPlaceholder: () => String(blockController.getSpacing("gap", { nativeOnly: false, cascading: true })),
	setModelValue: (value: string | boolean | number) => {
		if (typeof value === "boolean") return;
		blockController.setSpacing("gap", String(value));
	},
};

const layoutSectionProperties = [
	{
		component: StylePropertyControl,
		condition: () => !blockController.isText(),
		getProps: () => {
			return {
				propertyKey: "display",
				component: OptionToggle,
				label: __("Type"),
				enableStates: false,
				options: [
					{
						label: __("Stack"),
						value: "flex",
					},
					{
						label: __("Grid"),
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
		getProps: () => ({ gapProps }),
		usedStyleProperties: [
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
		getProps: () => ({ gapProps }),
		usedStyleProperties: [
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
	name: __("Layout"),
	properties: layoutSectionProperties,
	condition: () =>
		!blockController.multipleBlocksSelected() &&
		!blockController.isHTML() &&
		!blockController.isImage() &&
		!blockController.isSVG() &&
		!blockController.isVideo() &&
		!blockController.isInput(),
};
