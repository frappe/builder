import blockController from "@/utils/blockController";
import { computed } from "vue";
import PropertyControl from "../Controls/PropertyControl.vue";

const linkSectionProperties = [
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Link To",
				styleProperty: "href",
				enableStates: false,
				allowDynamicValue: true,
				controlType: "attribute",
				getModelValue: () => blockController.getAttribute("href"),
				setModelValue: (val: string) => {
					if (val && !blockController.isLink()) {
						blockController.convertToLink();
					}
					if (!val && blockController.isLink()) {
						blockController.unsetLink();
					} else {
						blockController.setAttribute("href", val);
					}
				},
			};
		},
		searchKeyWords: "Link, Href, URL",
		events: {
			setDynamicValue: () => {
				if (!blockController.isLink()) {
					blockController.convertToLink();
				}
			},
			clearDynamicValue: () => {
				if (blockController.isLink() && !blockController.getAttribute("href")) {
					blockController.unsetLink();
				}
			},
		},
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Opens in",
				controlType: "attribute",
				type: "select",
				styleProperty: "target",
				allowDynamicValue: false,
				getModelValue: () => blockController.getAttribute("target") || "_self",
				setModelValue: (val: string) => {
					if (val === "_self") {
						blockController.removeAttribute("target");
					} else {
						blockController.setAttribute("target", val);
					}
				},
				options: [
					{
						value: "_self",
						label: "Same Tab",
					},
					{
						value: "_blank",
						label: "New Tab",
					},
				],
			};
		},
		searchKeyWords: "Link, Target, Opens in, OpensIn, Opens In, New Tab",
		condition: () => blockController.getAttribute("href"),
	},
];

export default {
	name: "Link",
	properties: linkSectionProperties,
	collapsed: computed(() => !blockController.isLink()),
	condition: () =>
		!blockController.multipleBlocksSelected() &&
		!blockController.getSelectedBlocks()[0].parentBlock?.isLink(),
};
