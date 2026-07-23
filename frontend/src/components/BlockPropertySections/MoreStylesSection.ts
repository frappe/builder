import MoreStylesPanel from "@/components/MoreStylesPanel.vue";
import blockController from "@/utils/blockController";
import { getNonCuratedProperties } from "@/utils/curatedStyleProperties";
import { computed } from "vue";

const moreStylesSectionProperties = [
	{
		component: MoreStylesPanel,
		searchKeyWords: "More, Styles, CSS, Property, Properties, Advanced",
	},
];

export default {
	name: "More Styles",
	properties: moreStylesSectionProperties,
	collapsed: computed(() => {
		const block = blockController.getFirstSelectedBlock();
		if (!block) return true;
		const styles = { ...block.baseStyles, ...block.tabletStyles, ...block.mobileStyles };
		return getNonCuratedProperties(styles).size === 0;
	}),
	condition: () => blockController.getSelectedBlocks().length === 1
};
