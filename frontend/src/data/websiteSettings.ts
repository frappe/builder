import { createDocumentResource } from "frappe-ui";

const websiteSettings = createDocumentResource({
	doctype: "Website Settings",
	name: "Website Settings",
	auto: false,
});

export { websiteSettings };
