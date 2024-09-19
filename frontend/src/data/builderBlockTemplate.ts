import { createListResource } from "frappe-ui";

const builderBlockTemplate = createListResource({
	method: "GET",
	doctype: "Block Template",
	fields: ["template_name", "category", "preview", "name", "preview_width", "preview_height"],
	orderBy: "`order`",
	cache: "blockTemplates",
	start: 0,
	pageLength: 100,
});

export default builderBlockTemplate;
