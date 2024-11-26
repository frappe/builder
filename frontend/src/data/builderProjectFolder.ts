import { createListResource } from "frappe-ui";

const builderProjectFolder = createListResource({
	method: "GET",
	doctype: "Builder Project Folder",
	fields: ["folder_name"],
	orderBy: "`folder_name`",
	cache: "builderProjectFolder",
	start: 0,
	pageLength: 100,
	auto: true,
});

export default builderProjectFolder;
