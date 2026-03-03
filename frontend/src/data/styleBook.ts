import { createListResource } from "frappe-ui";

const styleBook = createListResource({
	method: "GET",
	doctype: "Builder Style Book",
	fields: ["style", "element", "font_family", "font_size", "font_weight", "line_height"],
	cache: "styleBook",
	start: 0,
	pageLength: 50,
	auto: true,
});

export default styleBook;
