import BlockPositionHandler from "@/components/BlockPositionHandler.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import { __ } from "@/translation";

const position = () => String(blockController.getStyle("position"));
const isPositioned = () => ["relative", "absolute", "fixed", "sticky"].includes(position());
// z-index also stacks the items of a flex or grid parent, positioned or not
const isLayoutItem = () => {
	const parent = blockController.getParentBlock();
	return Boolean(parent?.isFlex() || parent?.isGrid());
};

// the block the section was open for, so switching it to Auto or Relative doesn't fold it away
let openFor: string | undefined;

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
		// z-index orders positioned blocks and layout items; one already set stays editable
		condition: () => isPositioned() || isLayoutItem() || Boolean(blockController.getStyle("zIndex")),
	},
];

export default {
	name: __("Position"),
	properties: positionSectionProperties,
	condition: () => !blockController.multipleBlocksSelected() && !blockController.isRoot(),
	// open where the section has pins or offsets to show, until another block is selected
	collapsed: computed(() => {
		const blockId = blockController.getFirstSelectedBlock()?.blockId;
		if (["absolute", "fixed", "sticky"].includes(position())) openFor = blockId;
		return openFor !== blockId;
	}),
};
