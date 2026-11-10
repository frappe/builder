import { getFormStateVariantProperty } from "@/components/BlockPropertySections/FormStateSection";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

export default {
	name: __("Button"),
	properties: [
		getFormStateVariantProperty(
			"default",
			__("Variant"),
			__("The layer of this button shown until its form is submitted."),
		),
	],
	condition: () => blockController.hasFormStateVariants() && !blockController.multipleBlocksSelected(),
};
