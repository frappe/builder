import { createListResource } from "frappe-ui";

const moduleDef = createListResource({
	method: "GET",
	doctype: "Module Def",
	fields: ["name", "module_name"],
	orderBy: "module_name",
	cache: "moduleDef",
	start: 0,
	pageLength: 200,
	auto: true,
});

export default moduleDef;
