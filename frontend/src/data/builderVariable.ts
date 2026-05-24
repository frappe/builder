import { createListResource } from "frappe-ui";

const builderVariables = createListResource({
	method: "GET",
	doctype: "Builder Variable",
	fields: ["name", "variable_name", "value", "type", "is_standard", "dark_value", "group", "description"],
	cache: "builderVariables",
	start: 0,
	pageLength: 500,
	auto: true,
	orderBy: "creation desc",
});

export default builderVariables;
