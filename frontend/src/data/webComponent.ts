import { createListResource } from "frappe-ui";

const webComponent = createListResource({
	method: "GET",
	doctype: "Builder Component",
	fields: ["component_name", "block", "name", "for_web_page", "component_id"],
	orderBy: "modified desc",
	cache: "components",
	start: 0,
	pageLength: 100,
	auto: true,
});

export default webComponent;
