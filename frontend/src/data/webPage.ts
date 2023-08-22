import { createListResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Web Page Beta",
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
	],
	auto: true,
	cache: "pages",
	orderBy: "creation desc",
	pageLength: 50,
});

export { webPages };
