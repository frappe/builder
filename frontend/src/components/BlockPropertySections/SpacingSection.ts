import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import blockController from "@/utils/blockController";

const SPLITS = ["T", "R", "B", "L"];

const getMergedValue = (parts: StyleValue[]) => parts[0] ?? 0;

const spacingSectionProperties = [
	{
		component: SplitPropertyControl,
		searchKeyWords: "Margin, Top, MarginTop, Margin Top",
		getProps: () => {
			return {
				label: "Margin",
				propertyKey: "margin",
				splits: SPLITS,
				inputAttrs: {},
				getModelValue: (state: string | null = null) =>
					state
						? String(blockController.getNativeStyle(`${state}:margin`) ?? "")
						: String(blockController.getMargin({ nativeOnly: true, cascading: false })),
				getPlaceholder: () => String(blockController.getMargin({ nativeOnly: false, cascading: true })),
				getMergedValue,
				setModelValue: (value: string | boolean | number) => {
					if (typeof value === "boolean") return;
					blockController.setMargin(String(value));
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
				label: "Padding",
				propertyKey: "padding",
				splits: SPLITS,
				inputAttrs: { min: 0 },
				getModelValue: (state: string | null = null) =>
					state
						? String(blockController.getNativeStyle(`${state}:padding`) ?? "")
						: String(blockController.getPadding({ nativeOnly: true, cascading: false })),
				getPlaceholder: () => String(blockController.getPadding({ nativeOnly: false, cascading: true })),
				getMergedValue,
				setModelValue: (value: string | boolean | number) => {
					if (typeof value === "boolean") return;
					blockController.setPadding(String(value));
				},
			};
		},
		usedStyleProperties: ["padding", "padding-bottom", "padding-left", "padding-right", "padding-top"],
	},
];

export default {
	name: "Spacing",
	properties: spacingSectionProperties,
};
