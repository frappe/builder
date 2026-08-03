import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";

const transitionSectionProperties = [
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "速度",
				propertyKey: "transitionDuration",
				type: "select",
				enableStates: false,
				options: [
					{ value: null, label: "无" },
					{ value: "150ms", label: "快" },
					{ value: "300ms", label: "正常" },
					{ value: "500ms", label: "慢" },
					{ value: "1000ms", label: "非常慢" },
				],
				setModelValue: (val: string | null) => {
					if (val === "None") {
						val = null;
					}
					blockController.setStyle("transitionDuration", val);
					if (val) {
						if (!blockController.getStyle("transitionTimingFunction")) {
							blockController.setStyle("transitionTimingFunction", "ease");
						}
						if (!blockController.getStyle("transitionProperty")) {
							blockController.setStyle("transitionProperty", "all");
						}
					} else {
						blockController.setStyle("transitionTimingFunction", null);
						blockController.setStyle("transitionProperty", null);
					}
				},
			};
		},
		searchKeyWords: "Transition, Duration, Speed, Animation Time",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "缓动",
				propertyKey: "transitionTimingFunction",
				type: "select",
				enableStates: false,
				options: [
					{ value: "ease", label: "平滑" },
					{ value: "linear", label: "线性" },
					{ value: "ease-in", label: "渐入" },
					{ value: "ease-out", label: "渐出" },
					{ value: "ease-in-out", label: "渐入渐出" },
				],
			};
		},
		searchKeyWords: "Transition, Timing, Easing, Animation Style",
		condition: () => blockController.getStyle("transitionDuration"),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "属性",
				propertyKey: "transitionProperty",
				type: "select",
				enableStates: false,
				options: [
					{ value: "all", label: "所有属性" },
					{ value: "transform", label: "仅变换" },
					{ value: "opacity", label: "仅不透明度" },
					{ value: "background", label: "仅背景" },
					{ value: "colors", label: "仅颜色" },
				],
			};
		},
		searchKeyWords: "Transition, Properties, What to Animate",
		condition: () => blockController.getStyle("transitionDuration"),
	},
];

export default {
	name: "过渡",
	properties: transitionSectionProperties,
	collapsed: true,
	condition: () => !blockController.multipleBlocksSelected(),
};
