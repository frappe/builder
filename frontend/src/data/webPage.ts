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
		"is_template",
		"owner",
	],
	filters: {
		is_template: 0,
	},
	cache: "pages",
	pageLength: 50,
});

const templates = createListResource({
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
		"published",
		"dynamic_route",
		"modified",
		"is_template",
		"template_name",
		"owner",
	],
	filters: {
		is_template: 1,
	},
	cache: "templates",
	orderBy: "modified desc",
	pageLength: 50,
	auto: true,
});
export { templates, webPages };
