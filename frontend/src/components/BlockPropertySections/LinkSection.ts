import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { computed, nextTick } from "vue";

const linkSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Link To",
				showInputAsOption: true,
				modelValue: blockController.getAttribute("href"),
			};
		},
		searchKeyWords: "Link, Href, URL",
		events: {
			"update:modelValue": async (val: string) => {
				if (val && !blockController.isLink()) {
					blockController.convertToLink();
					await nextTick();
					await nextTick();
				}
				if (!val && blockController.isLink()) {
					blockController.unsetLink();
				} else {
					blockController.setAttribute("href", val);
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
		!blockController.getSelectedBlocks()[0].parentBlock?.isLink() &&
		!blockController.isForm(),
};
