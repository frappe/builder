import { createListResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: [
		"name",
		"route",
		"page_name",
		"preview",
		"page_title",
		"creation",
		"published",
		"dynamic_route",
		"modified_by",
		"modified",
		"owner",
	],
	auto: true,
	cache: "pages",
	orderBy: "modified desc",
	pageLength: 50,
});

export { webPages };
