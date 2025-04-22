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
				const formBlock = blockController.getFirstSelectedBlock();
				if (!formBlock) return;
				const webFormResource = await createDocumentResource({
					doctype: "Web Form",
					name: webform,
					auto: true,
				});
				await webFormResource.get.promise;
				const webForm = webFormResource.doc;
				console.log(webForm);
				formBlock.children = [];
				let section = formBlock.addChild(getBlockTemplate("section"), null, false);
				let column = section.addChild(getBlockTemplate("column"), null, false);
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
						// create structure based on sectionbreak and column break
						// on section break, there should be a wrapping div with flex-direction: column
						// on column break, parent should be a div with flex-direction: column
						if (df.fieldtype === "Section Break") {
							section = formBlock.addChild(getBlockTemplate("section"), null, false);
							column = section.addChild(getBlockTemplate("column"), null, false);
						} else if (df.fieldtype === "Column Break") {
							column = section.addChild(getBlockTemplate("column"), null, false);
						} else {
							const field = field_map[df.fieldtype] || "input";
							if (field === "input") {
								df.input_type =
									df.fieldtype === "int"
										? "number"
										: df.fieldtype === "Data" && df.options === "Email"
										? "email"
										: "text";
							}
							column.addChild(getBlockTemplate(field, df), null, false);
						}
					},
				);
				formBlock.addChild(getBlockTemplate("button"), null, false);
				formBlock.setAttribute("data-web-form", webform);
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
