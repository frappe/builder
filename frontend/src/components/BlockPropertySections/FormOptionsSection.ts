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
				for (const key in webForm.web_form_fields) {
					block.addChild(
						getBlockTemplate("input", {
							type: "text",
						}),
					);
				}
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
