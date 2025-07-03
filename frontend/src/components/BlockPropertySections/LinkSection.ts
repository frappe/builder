import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import StyleControl from "../Controls/StyleControl.vue";

const linkSectionProperties = [
	{
		component: StyleControl,
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
		component: InlineInput,
		getProps: () => {
			return {
				label: "Opens in",
				type: "select",
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
				modelValue: blockController.getAttribute("target") || "_self",
			};
		},
		searchKeyWords: "Link, Target, Opens in, OpensIn, Opens In, New Tab",
		events: {
			"update:modelValue": (val: string) => {
				if (val === "_self") {
					blockController.removeAttribute("target");
				} else {
					blockController.setAttribute("target", val);
				}
			},
		},
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
