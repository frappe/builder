import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import { createDocumentResource } from "frappe-ui";

const formOptionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			// form based on
			return {
				label: "Based On",
				type: "select",
				options: [
					{
						value: "doctype",
						label: "DocType",
					},
					{
						value: "webform",
						label: "Web Form",
					},
					{
						value: "custom",
						label: "Custom",
					},
				],
				modelValue: blockController.getFormOption("based_on") || "custom",
			};
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Webform",
				type: "select",
				options: [
					{
						value: "enquire",
						label: "Enquire",
					},
					{
						value: "edit-profile",
						label: "Update Profile",
					},
				],
				modelValue: blockController.getFormOption("reference_document"),
			};
		},
		searchKeyWords: "Form, Webform, Web Form, Reference Form",
		events: {
			"update:modelValue": async (webform: string) => {
				const block = blockController.getFirstSelectedBlock();
				if (!block) return;
				const webFormResource = await createDocumentResource({
					doctype: "Web Form",
					name: webform,
					auto: true,
				});
				await webFormResource.get.promise;
				const webForm = webFormResource.doc;
				console.log(webForm);
				block.children = [];
				webForm.web_form_fields.forEach(
					(df: {
						fieldname: string;
						label: string;
						fieldtype: string;
						options: string;
						reqd: boolean;
						input_type?: string;
					}) => {
						const field_map = {
							Data: "input",
							Select: "select",
							Link: "select",
							"Small Text": "textarea",
							"Long Text": "textarea",
							int: "input",
						} as any;
						const field = field_map[df.fieldtype] || "input";
						if (field === "input") {
							df.input_type =
								df.fieldtype === "int"
									? "number"
									: df.fieldtype === "Data" && df.options === "Email"
									? "email"
									: "text";
						}
						block.addChild(getBlockTemplate(field, df));
					},
				);
				block.addChild(getBlockTemplate("button"));
				blockController.setFormOption("reference_document", webform);
			},
		},
	},
] as BlockProperty[];

export default {
	name: "Form Options",
	properties: formOptionsSectionProperties,
	condition: () => blockController.isForm() && !blockController.multipleBlocksSelected(),
};
