import { BuilderPage } from "@/types/doctypes";
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

// unlike the home page picker, a link may point at a page that isn't live yet:
// its route is already set, so the link works once the page is published
const linkablePages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "route"],
	filters: {
		is_template: 0,
		dynamic_route: 0,
	},
	cache: "linkable-pages",
	pageLength: 9999,
	auto: true,
});

const getLinkablePageOptions = () =>
	(linkablePages.data || [])
		.filter((page: BuilderPage) => page.route)
		.map((page: BuilderPage) => ({ label: `/${page.route}`, value: `/${page.route}` }));

export { allWebPages, getLinkablePageOptions, linkablePages };
