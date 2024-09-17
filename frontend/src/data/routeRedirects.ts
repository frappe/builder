import { createListResource } from "frappe-ui";

const routeRedirects = createListResource({
	method: "GET",
	doctype: "Website Route Redirect",
	parent: "Website Settings",
	fields: ["source", "target", "redirect_http_status", "name"],
	orderBy: "modified desc",
	cache: "routeRedirects",
	start: 0,
	pageLength: 100,
	auto: true,
});

export default routeRedirects;
