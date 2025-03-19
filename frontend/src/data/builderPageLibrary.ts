import { createListResource } from "frappe-ui";

const builderProjectFolder = createListResource({
	method: "GET",
	doctype: "Builder Page Library",
	fields: ["library_url", "library_type"],
	cache: "builderPageLibrary",
	start: 0,
	pageLength: 100,
	auto: true,
});

export default builderProjectFolder;
