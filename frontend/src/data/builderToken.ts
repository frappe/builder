import { createListResource } from "frappe-ui";

const builderTokens = createListResource({
	method: "GET",
	doctype: "Builder Token",
	fields: ["name", "token_name", "value", "type", "is_standard", "dark_value", "group"],
	cache: "builderTokens",
	start: 0,
	pageLength: 500,
	auto: true,
	orderBy: "creation desc",
});

export default builderTokens;
