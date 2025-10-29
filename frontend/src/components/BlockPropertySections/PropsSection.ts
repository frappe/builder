import PropsEditor from "../PropsEditor.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const propsSection = [
	{
		component: PropsEditor,
		getProps: () => {
			return {
				obj: blockController.getBlockProps(),
				description: `
					<b>Note:</b>
					<br />
					<br />
					• A block can have multiple props
					<br />
					• Props can be static values, dynamic values (from data script), or inherited from ancestor blocks
				`,
			};
		},
		searchKeyWords: "Props, Interface Props, Properties, Block Props, Block Properties",
		events: {
			"update:obj": (obj: BlockProps) => blockController.setBlockProps(obj), // TODO: race condition?
			"update:ancestorUpdateDependency": (
				propKey: string,
				action: "add" | "remove", // TODO: better name?
			) => blockController.updateBlockPropsDependencyForAncestor(propKey, action),
		},
	},
];

export default {
	name: "Props",
	properties: propsSection,
	collapsed: computed(() => {
		return Object.keys(blockController.getBlockProps()).length === 0;
	}),
	condition: () => !blockController.multipleBlocksSelected(),
};
