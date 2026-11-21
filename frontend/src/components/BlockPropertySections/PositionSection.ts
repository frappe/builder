import BlockPositionHandler from "@/components/BlockPositionHandler.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import { __ } from "@/translation";

const position = () => String(blockController.getStyle("position"));

const positionSectionProperties = [
	{
		component: BlockPositionHandler,
		searchKeyWords:
			"Position, Top, Right, Bottom, Left, PositionTop, Position Top, PositionRight, Position Right, PositionBottom, Position Bottom, PositionLeft, Position Left, Free, Fixed, Absolute, Relative, Sticky, Pin, Pins, Anchor, Stretch, Center, Fill",
		getProps: () => {},
		usedStyleProperties: ["bottom", "left", "position", "right", "top"],
	},
];

export default {
	name: __("Position"),
	properties: positionSectionProperties,
	condition: () => !blockController.multipleBlocksSelected() && !blockController.isRoot(),
	// open where the section has pins or offsets to show
	collapsed: computed(() => !["absolute", "fixed", "sticky"].includes(position())),
};
