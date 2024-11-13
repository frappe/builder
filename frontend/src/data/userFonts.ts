import { createListResource } from "frappe-ui";

const userFont = createListResource({
	method: "GET",
	doctype: "User Font",
	fields: ["font_name", "font_file"],
	cache: "userFonts",
	start: 0,
	pageLength: 50,
});

export default userFont;
