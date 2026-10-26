import type Block from "@/block";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

const radioGroupOptionsSectionProperties = [
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: __("Required"),
				options: [
					{ label: __("Yes"), value: true },
					{ label: __("No"), value: false },
				],
				modelValue: blockController.getSharedValue((block) => block.isGroupRequired()),
			};
		},
		searchKeyWords: "Required, Mandatory, Validation, Radio, Radio Group, form",
		events: {
			"update:modelValue": (val: boolean) =>
				blockController.getSelectedBlocks().forEach((block: Block) => block.setGroupRequired(val)),
		},
	},
];

export default {
	name: __("Radio Group"),
	properties: radioGroupOptionsSectionProperties,
	condition: () => blockController.isRadioGroup(),
};
