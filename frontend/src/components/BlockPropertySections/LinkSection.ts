import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import blockController from "@/utils/blockController";
import { Switch } from "frappe-ui";
import { computed } from "vue";

const linkSectionProperties = [
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				label: "链接到",
				propertyKey: "href",
				allowDynamicValue: true,
				getModelValue: () => blockController.getAttribute("href"),
				setModelValue: async (val: string) => {
					if (val && !blockController.isLink()) {
						await blockController.convertToLink();
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
		component: AttributePropertyControl,
		getProps: () => {
			return {
				label: "打开方式",
				type: "select",
				propertyKey: "target",
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
						label: "当前标签",
					},
					{
						value: "_blank",
						label: "新标签页",
					},
				],
			};
		},
		searchKeyWords: "Link, Target, Opens in, OpensIn, Opens In, New Tab",
		condition: () => blockController.getAttribute("href"),
	},
	{
		component: Switch,
		getProps: () => {
			return {
				label: "跟踪点击",
				size: "sm",
				class: "[&_label]:text-xs [&_label]:text-ink-gray-6 [&_label]:font-normal",
				modelValue: blockController.isClickTrackingEnabled(),
			};
		},
		searchKeyWords: "Track, Clicks, Tracking, Analytics, CTR, Click Tracking",
		events: {
			"update:modelValue": (val: boolean) => blockController.toggleClickTracking(val),
		},
	},
];

export default {
	name: "链接",
	properties: linkSectionProperties,
	collapsed: computed(() => !blockController.isLink()),
	condition: () =>
		!blockController.multipleBlocksSelected() &&
		!blockController.getSelectedBlocks()[0].parentBlock?.isLink() &&
		!(blockController.isHTML() && !blockController.isSVG()),
};
