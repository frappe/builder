import { createListResource } from "frappe-ui";

const styleTokens = createListResource({
	method: "GET",
	doctype: "Style Token",
	fields: ["name", "token_name", "value", "type"],
	cache: "cssVariabless",
	start: 0,
	pageLength: 50,
	auto: true,
	orderBy: "token_name",
});

export default styleTokens;
