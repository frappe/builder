import { createListResource, createResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: [
		"name",
		"route",
		"page_name",
		"preview",
		"page_title",
		"meta_image",
		"creation",
		"published",
		"dynamic_route",
		"modified_by",
		"modified",
		"is_template",
		"authenticated_access",
		"project_folder",
		"is_standard",
		"owner",
	],
	filters: {
		is_template: 0,
	},
	cache: "pages",
	pageLength: 50,
});

const templateGroups = createResource({
	url: "builder.api.get_template_groups",
	cache: "template-groups",
});

const searchablePages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "route", "page_name", "page_title"],
	filters: {
		is_template: 0,
	},
	cache: "searchable-pages",
	orderBy: "modified desc",
	pageLength: 10,
});

export { searchablePages, templateGroups, webPages };
