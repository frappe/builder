import { createDocumentResource } from "frappe-ui";

const builderSettings = createDocumentResource({
	doctype: "Builder Settings",
	name: "Builder Settings",
	cache: "builderSettings",
	auto: false,
});

export { builderSettings };
