import ObjectEditor from "@/components/ObjectEditor.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const customAttributesSectionProperties = [
	{
		component: ObjectEditor,
		getProps: () => {
			return {
				obj: blockController.getCustomAttributes() as Record<string, string>,
			};
		},
		searchKeyWords: "Attributes, CustomAttributes, Custom Attributes, HTML Attributes, Data Attributes",
		events: {
			"update:obj": (obj: Record<string, string>) => blockController.setCustomAttributes(obj),
		},
	},
];

export default {
	name: "HTML Attributes",
	properties: customAttributesSectionProperties,
	collapsed: computed(() => {
		return Object.keys(blockController.getCustomAttributes()).length === 0;
	}),
};
