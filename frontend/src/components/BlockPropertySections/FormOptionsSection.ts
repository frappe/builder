import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import { createDocumentResource } from "frappe-ui";

const formOptionsSectionProperties = [
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
				modelValue: blockController.getFormOption("enquire"),
			};
		},
		searchKeyWords: "Action, URL",
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
					(df: { fieldname: string; label: string; fieldtype: string; options: string; reqd: boolean }) => {
						const field_map = {
							Data: "input",
							Select: "select",
							Link: "select",
							"Small Text": "input",
						} as any;
						const field = field_map[df.fieldtype] || "input";
						block.addChild(
							getBlockTemplate(field, {
								type: "text",
							}),
						);
					},
				);
				blockController.setFormOption("enquire", webform);
			},
		},
	},
] as BlockProperty[];

export default {
	name: "Web Form Options",
	properties: formOptionsSectionProperties,
	condition: () => blockController.isForm(),
};
