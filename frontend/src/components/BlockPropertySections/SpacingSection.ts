import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

const SPLITS = ["T", "R", "B", "L"];

const spacingSectionProperties = [
	{
		component: SplitPropertyControl,
		searchKeyWords: "Margin, Top, MarginTop, Margin Top",
		getProps: () => {
			return {
				label: __("Margin"),
				propertyKey: "margin",
				splits: SPLITS,
				inputAttrs: {},
				getModelValue: (state: string | null = null) =>
					state
						? String(blockController.getNativeStyle(`${state}:margin`) ?? "")
						: String(blockController.getSpacing("margin", { nativeOnly: true, cascading: false })),
				getPlaceholder: () =>
					String(blockController.getSpacing("margin", { nativeOnly: false, cascading: true })),
				setModelValue: (value: string | boolean | number) => {
					if (typeof value === "boolean") return;
					blockController.setSpacing("margin", String(value));
				},
			};
		},
		usedStyleProperties: ["margin", "margin-bottom", "margin-left", "margin-right", "margin-top"],
		condition: () => !blockController.isRoot(),
	},
	{
		component: SplitPropertyControl,
		searchKeyWords: "Padding, Top, PaddingTop, Padding Top",
		getProps: () => {
			return {
				label: __("Padding"),
				propertyKey: "padding",
				splits: SPLITS,
				inputAttrs: { min: 0 },
				getModelValue: (state: string | null = null) =>
					state
						? String(blockController.getNativeStyle(`${state}:padding`) ?? "")
						: String(blockController.getSpacing("padding", { nativeOnly: true, cascading: false })),
				getPlaceholder: () =>
					String(blockController.getSpacing("padding", { nativeOnly: false, cascading: true })),
				setModelValue: (value: string | boolean | number) => {
					if (typeof value === "boolean") return;
					blockController.setSpacing("padding", String(value));
				},
			};
		},
		usedStyleProperties: ["padding", "padding-bottom", "padding-left", "padding-right", "padding-top"],
	},
];

export default {
	name: __("Spacing"),
	properties: spacingSectionProperties,
};
