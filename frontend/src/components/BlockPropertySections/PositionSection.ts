import BlockPositionHandler from "@/components/BlockPositionHandler.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import { __ } from "@/translation";

const position = () => String(blockController.getStyle("position"));
const isPositioned = () => ["relative", "absolute", "fixed", "sticky"].includes(position());

const positionSectionProperties = [
	{
		component: BlockPositionHandler,
		searchKeyWords:
			"Position, Top, Right, Bottom, Left, PositionTop, Position Top, PositionRight, Position Right, PositionBottom, Position Bottom, PositionLeft, Position Left, Free, Fixed, Absolute, Relative, Sticky, Pin, Pins, Anchor, Stretch, Center, Fill",
		getProps: () => {},
		usedStyleProperties: ["bottom", "left", "position", "right", "top"],
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Z-Index"),
				propertyKey: "zIndex",
			};
		},
		searchKeyWords: "Z, Index, ZIndex, Z Index, Z-index, Z-Index, Layer, Stack, Order",
		// z-index only orders positioned blocks; one already set stays editable
		condition: () => isPositioned() || Boolean(blockController.getStyle("zIndex")),
	},
];

export default {
	name: __("Position"),
	properties: positionSectionProperties,
	condition: () => !blockController.multipleBlocksSelected() && !blockController.isRoot(),
	// open where the section has pins or offsets to show
	collapsed: computed(() => !["absolute", "fixed", "sticky"].includes(position())),
};
