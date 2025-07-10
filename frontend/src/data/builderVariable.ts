import { createListResource } from "frappe-ui";

const builderVariables = createListResource({
	method: "GET",
	doctype: "Builder Variable",
	fields: ["name", "variable_name", "value", "type", "is_standard"],
	cache: "cssVariabless",
	start: 0,
	pageLength: 50,
	auto: true,
	orderBy: "variable_name",
});

export default builderVariables;
