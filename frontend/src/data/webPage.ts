import { createListResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: [
		"name",
		"route",
		"blocks",
		"page_name",
		"preview",
		"page_title",
		"creation",
		"page_data_script",
		"draft_blocks",
		"published",
		"dynamic_route",
		"client_scripts",
		"modified",
	],
	cache: "pages",
	orderBy: "modified desc",
	pageLength: 50,
});

export { webPages };
