import { createListResource } from "frappe-ui";

const builderVariables = createListResource({
	method: "GET",
	doctype: "Builder Variable",
	fields: ["name", "token_name", "value", "type"],
	cache: "cssVariabless",
	start: 0,
	pageLength: 50,
	auto: true,
	orderBy: "token_name",
});

export default builderVariables;
