import BlockPositionHandler from "@/components/BlockPositionHandler.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const positionSectionProperties = [
	{
		component: BlockPositionHandler,
		searchKeyWords:
			"Position, Top, Right, Bottom, Left, PositionTop, Position Top, PositionRight, Position Right, PositionBottom, Position Bottom, PositionLeft, Position Left, Free, Fixed, Absolute, Relative, Sticky",
		getProps: () => {},
	},
];

export default {
	name: "Position",
	properties: positionSectionProperties,
	condition: () => !blockController.multipleBlocksSelected() && !blockController.isRoot(),
	collapsed: computed(() => {
		return (
			!blockController.getStyle("top") &&
			!blockController.getStyle("right") &&
			!blockController.getStyle("bottom") &&
			!blockController.getStyle("left")
		);
	}),
};
