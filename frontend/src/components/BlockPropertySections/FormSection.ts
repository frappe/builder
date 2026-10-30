import type Block from "@/block";
import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import FormDestinationsInput from "@/components/Controls/FormDestinationsInput.vue";
import FormStatesInput from "@/components/Controls/FormStatesInput.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import { getLinkablePageOptions, linkablePages } from "@/data/allWebPages";
import blockController from "@/utils/blockController";
import { promptCreateFormDoctype } from "@/utils/dialogs";
import { checkFormDoctype } from "@/utils/formFields";
import { formStates } from "@/utils/formStates";
import { __ } from "@/translation";

const formSectionProperties = [
	{
		component: FormDestinationsInput,
		getProps: () => {
			return {
				label: __("Send to"),
				description: __("Each submission is saved, emailed or posted to these destinations."),
				modelValue: blockController.getFirstSelectedBlock().getFormDestinations(),
				createDoctype: () => promptCreateFormDoctype(blockController.getFirstSelectedBlock()),
				checkDoctype: (doctype: string, createDoctype?: () => void) =>
					checkFormDoctype(blockController.getFirstSelectedBlock(), doctype, createDoctype),
			};
		},
		searchKeyWords:
			"Send to, Email, Webhook, DocType, Save, Database, Submissions, Notify, Destination, form",
		events: {
			"update:modelValue": (destinations: FormDestination[]) =>
				blockController
					.getSelectedBlocks()
					.forEach((block: Block) => block.setFormDestinations(destinations)),
		},
		condition: () => blockController.isForm(),
	},
	{
		component: AttributePropertyControl,
		getProps: () => {
			return {
				label: __("Redirect"),
				propertyKey: "data-redirect",
				component: Autocomplete,
				options: getLinkablePageOptions(),
				onFocus: () => linkablePages.reload(),
				showInputAsOption: true,
				placeholder: __("URL or /page"),
				getModelValue: () => blockController.getEffectiveAttribute("data-redirect") || "",
				setModelValue: (val: string) =>
					blockController.setEffectiveAttribute("data-redirect", val || undefined),
			};
		},
		searchKeyWords: "Redirect, After Submit, Thank You, Success Page, URL, form",
		condition: () => blockController.isForm(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: __("Preview"),
				type: "select",
				options: formStates,
				modelValue: blockController.getFirstSelectedBlock().getFormStatePreview(),
				description: __("Shows the form on the canvas as visitors see it in this state."),
			};
		},
		searchKeyWords: "State, Form State, Sending, Loading, Success, Error, Preview, form",
		events: {
			"update:modelValue": (state: string) => blockController.setFormStatePreview(state),
		},
		condition: () => !blockController.isForm(),
	},
	{
		component: FormStatesInput,
		getProps: () => {
			return {
				label: __("Show in"),
				modelValue: blockController.getFirstSelectedBlock().getFormStates(),
				description: __("The form states this block is visible in."),
			};
		},
		searchKeyWords: "Show in, Visible, Hide, Success Message, Error Message, Sending, State, form",
		events: {
			"update:modelValue": (states: string[]) =>
				blockController.getSelectedBlocks().forEach((block: Block) => block.setFormStates(states)),
		},
		condition: () => !blockController.isForm(),
	},
];

export default {
	name: __("Form"),
	properties: formSectionProperties,
	// a field is set up in its own Input section, and a button with variants in Form State, as in Framer
	condition: () =>
		blockController.isInForm() && !blockController.isInFormField() && !blockController.hasFormStateVariants(),
};
