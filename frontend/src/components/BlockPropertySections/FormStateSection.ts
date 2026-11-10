import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { formStates } from "@/utils/formStates";
import { __ } from "@/translation";

// picks the variant a button shows in one state of its form, as Framer's Form state on a button
export const getFormStateVariantProperty = (state: string, label: string, description: string) => ({
	component: InlineInput,
	getProps: () => {
		const button = blockController.getFirstSelectedBlock();
		return {
			label,
			type: "select",
			options: button.getChildren().map((variant) => ({
				label: variant.getBlockDescription(),
				value: variant.blockId,
			})),
			modelValue: button.getFormStateVariant(state)?.blockId,
			description,
		};
	},
	searchKeyWords: `Form State, Variant, Button, ${label}, Loading, Spinner, Thank You, form`,
	events: {
		"update:modelValue": (variantId: string) =>
			blockController.getFirstSelectedBlock().setFormStateVariant(state, variantId),
	},
});

// as in Framer, only Sending and Success are picked here; default is the Button section's Variant
const formStateSectionProperties = formStates
	.filter((state) => state.value === "sending" || state.value === "success")
	.map((state) =>
		getFormStateVariantProperty(
			state.value,
			state.label,
			__("The layer of this button shown in this form state."),
		),
	);

export default {
	name: __("Form State"),
	properties: formStateSectionProperties,
	condition: () => blockController.hasFormStateVariants() && !blockController.multipleBlocksSelected(),
};
