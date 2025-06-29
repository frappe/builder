import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import { createDocumentResource, createListResource } from "frappe-ui";
import Autocomplete from "../Controls/Autocomplete.vue";

const formOptionsSectionProperties = [
	{
		component: Autocomplete,
		getProps: () => {
			return {
				label: "Webform",
				placeholder: "Select a Web Form",
				getOptions: async () => {
					const webForms = await createListResource({
						doctype: "Web Form",
						fields: ["name", "title"],
						limit: 100,
						orderBy: "title",
					});
					webForms.fetch();
					await webForms.list.promise;
					return webForms.data.map((doc: { title: string; name: string }) => ({
						label: doc.title,
						value: doc.name,
					}));
				},
				modelValue: blockController.getFormOption("reference_document"),
			};
		},
		searchKeyWords: "Form, Webform, Web Form, Reference Form",
		events: {
			"update:modelValue": async (webform: { label: string; value: string } | null) => {
				const formBlock = blockController.getFirstSelectedBlock();
				formBlock.setAttribute("data-web-form", webform?.value);
				blockController.setFormOption("reference_document", webform?.value);
				if (!formBlock || !webform) return;
				const webFormResource = await createDocumentResource({
					doctype: "Web Form",
					name: webform?.value,
					auto: true,
				});
				await webFormResource.get.promise;
				const webForm = webFormResource.doc;
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
			},
		},
	},
] as BlockProperty[];

export default {
	name: "Form Options",
	properties: formOptionsSectionProperties,
	condition: () => blockController.isForm() && !blockController.multipleBlocksSelected(),
};
