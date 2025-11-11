import { createListResource } from "frappe-ui";

const allWebPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "route"],
	filters: {
		is_template: 0,
		published: 1,
		authenticated_access: 0,
		dynamic_route: 0,
	},
	cache: "all_pages",
	pageLength: 100,
	auto: true,
});

export { allWebPages };
