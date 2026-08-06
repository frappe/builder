import BlockFlexLayoutHandler from "@/components/BlockFlexLayoutHandler.vue";
import BlockGridLayoutHandler from "@/components/BlockGridLayoutHandler.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";
import { collapseGapShorthand, expandGapShorthand } from "@/utils/cssUtils";
import StylePropertyControl from "../Controls/StylePropertyControl.vue";

const GAP_SPLITS = [{ label: "V" }, { label: "H" }];
const GAP_SPLITS_COLUMN = [{ label: "H" }, { label: "V" }];

// Gap is a spacing shorthand like margin and padding, but it renders here because it only exists
// on flex/grid containers. The splits lead with the axis items actually flow along, hence the
// flex-direction check; grid has none, which leaves it at vertical-then-horizontal.
const getGapProps = () => {
	const isColumnDirection = String(
		blockController.getNativeStyle("flexDirection") ||
			blockController.getCascadingStyle("flexDirection") ||
			"",
	).startsWith("column");
	return {
		label: "Gap",
		propertyKey: "gap",
		splitIcon: "lucide-layout-grid",
		splits: isColumnDirection ? GAP_SPLITS_COLUMN : GAP_SPLITS,
		toControlValues: (value: unknown) => {
			const [row, column] = expandGapShorthand(value);
			return isColumnDirection ? [column, row] : [row, column];
		},
		toModelValue: (parts: StyleValue[]) =>
			collapseGapShorthand(isColumnDirection ? [parts[1], parts[0]] : parts),
		getModelValue: (state: string | null = null) =>
			state
				? String(blockController.getNativeStyle(`${state}:gap`) ?? "")
				: String(blockController.getSpacing("gap", { nativeOnly: true, cascading: false })),
		getPlaceholder: () =>
			String(blockController.getSpacing("gap", { nativeOnly: false, cascading: true })),
		getMergedValue: (parts: StyleValue[]) => parts[0] ?? 0,
		setModelValue: (value: string | boolean | number) => {
			if (typeof value === "boolean") return;
			blockController.setSpacing("gap", String(value));
		},
	};
};

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
		getProps: () => ({ gapProps: getGapProps() }),
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
		getProps: () => ({ gapProps: getGapProps() }),
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
	name: "Layout",
	properties: layoutSectionProperties,
	condition: () => !blockController.multipleBlocksSelected() && !blockController.isHTML(),
};
