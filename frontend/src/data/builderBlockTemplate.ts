import { createListResource } from "frappe-ui";

const builderBlockTemplate = createListResource({
	method: "GET",
	doctype: "Block Template",
	fields: ["template_name", "category", "preview", "block", "name"],
	orderBy: "modified desc",
	cache: "blockTemplate",
	start: 0,
	pageLength: 100,
	auto: true,
});

export default builderBlockTemplate;
