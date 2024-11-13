import { createResource } from "frappe-ui";

const builderBlockTemplateList = createResource({
	method: "GET",
	url: "/api/method/builder.api.get_builder_block_templates",
	cache: "blockTemplates",
});

export default builderBlockTemplateList;
