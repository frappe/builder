import blockController from "@/utils/blockController";
import PropertyControl from "../Controls/PropertyControl.vue";

const transitionSectionProperties = [
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Duration",
				styleProperty: "transitionDuration",
				type: "select",
				enableStates: false,
				options: [
					{ value: null, label: "None" },
					{ value: "150ms", label: "Fast" },
					{ value: "300ms", label: "Normal" },
					{ value: "500ms", label: "Slow" },
					{ value: "1000ms", label: "Very Slow" },
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
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Timing",
				styleProperty: "transitionTimingFunction",
				type: "select",
				enableStates: false,
				options: [
					{ value: "ease", label: "Smooth" },
					{ value: "linear", label: "Linear" },
					{ value: "ease-in", label: "Ease In" },
					{ value: "ease-out", label: "Ease Out" },
					{ value: "ease-in-out", label: "Ease In Out" },
				],
			};
		},
		searchKeyWords: "Transition, Timing, Easing, Animation Style",
		condition: () => blockController.getStyle("transitionDuration"),
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Properties",
				styleProperty: "transitionProperty",
				type: "select",
				enableStates: false,
				options: [
					{ value: "all", label: "All Properties" },
					{ value: "transform", label: "Transform Only" },
					{ value: "opacity", label: "Opacity Only" },
					{ value: "background", label: "Background Only" },
					{ value: "colors", label: "Colors Only" },
				],
			};
		},
		searchKeyWords: "Transition, Properties, What to Animate",
		condition: () => blockController.getStyle("transitionDuration"),
	},
];

export default {
	name: "Transition",
	properties: transitionSectionProperties,
	collapsed: true,
	condition: () => !blockController.multipleBlocksSelected(),
};
