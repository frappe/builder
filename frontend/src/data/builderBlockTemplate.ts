import { createListResource } from "frappe-ui";

const builderBlockTemplate = createListResource({
	method: "GET",
	doctype: "Block Template",
	fields: ["template_name", "category", "preview", "block", "name", "preview_width", "preview_height"],
	orderBy: "modified desc",
	cache: "blockTemplate",
	start: 0,
	pageLength: 100,
	auto: true,
});

export default builderBlockTemplate;
