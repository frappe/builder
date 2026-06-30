import { createListResource, createResource } from "frappe-ui";

const webComponent = createListResource({
	method: "GET",
	doctype: "Builder Component",
	fields: [
		"component_name",
		"name",
		"for_web_page",
		"component_id",
		"is_standard",
		"preview",
		"preview_width",
		"preview_height",
		"category",
		"sort_order",
	],
	filters: {
		is_standard: 0,
	},
	orderBy: "modified desc",
	cache: "builderComponents",
	start: 0,
	pageLength: 100,
});

const standardComponent = createListResource({
	method: "GET",
	doctype: "Builder Component",
	fields: [
		"component_name",
		"name",
		"for_web_page",
		"component_id",
		"is_standard",
		"preview",
		"preview_width",
		"preview_height",
		"category",
		"sort_order",
	],
	filters: {
		is_standard: 1,
	},
	orderBy: "sort_order asc",
	cache: "standardBuilderComponents",
	start: 0,
	pageLength: 500,
});

const builderComponentCategories = createResource({
	url: "builder.api.get_builder_component_categories",
	cache: "builderComponentCategories",
});

export { builderComponentCategories, standardComponent };
export default webComponent;
