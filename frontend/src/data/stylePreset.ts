import { createListResource } from "frappe-ui";

const stylePreset = createListResource({
	method: "GET",
	doctype: "Builder Style Preset",
	fields: ["style_name", "style_map", "sort_order"],
	cache: "stylePresets",
	start: 0,
	pageLength: 50,
	auto: true,
	orderBy: "sort_order asc",
});

export default stylePreset;
