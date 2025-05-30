import { createListResource } from "frappe-ui/src/resources/listResource";

const webComponent = createListResource({
	method: "GET",
	doctype: "Builder Component",
	fields: ["component_name", "name", "for_web_page", "component_id"],
	orderBy: "modified desc",
	cache: "builderComponents",
	start: 0,
	pageLength: 100,
});

export default webComponent;
