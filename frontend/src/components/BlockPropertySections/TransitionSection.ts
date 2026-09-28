import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

const transitionSectionProperties = [
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Speed"),
				propertyKey: "transitionDuration",
				type: "select",
				enableStates: false,
				options: [
					{ value: null, label: __("None") },
					{ value: "150ms", label: __("Fast") },
					{ value: "300ms", label: __("Normal") },
					{ value: "500ms", label: __("Slow") },
					{ value: "1000ms", label: __("Very Slow") },
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
				label: __("Timing"),
				propertyKey: "transitionTimingFunction",
				type: "select",
				enableStates: false,
				options: [
					{ value: "ease", label: __("Smooth") },
					{ value: "linear", label: __("Linear") },
					{ value: "ease-in", label: __("Ease In") },
					{ value: "ease-out", label: __("Ease Out") },
					{ value: "ease-in-out", label: __("Ease In Out") },
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
				label: __("Properties"),
				propertyKey: "transitionProperty",
				type: "select",
				enableStates: false,
				options: [
					{ value: "all", label: __("All Properties") },
					{ value: "transform", label: __("Transform Only") },
					{ value: "opacity", label: __("Opacity Only") },
					{ value: "background", label: __("Background Only") },
					{ value: "colors", label: __("Colors Only") },
				],
			};
		},
		searchKeyWords: "Transition, Properties, What to Animate",
		condition: () => blockController.getStyle("transitionDuration"),
	},
];

export default {
	name: __("Transition"),
	properties: transitionSectionProperties,
	collapsed: true,
	condition: () => !blockController.multipleBlocksSelected(),
};
