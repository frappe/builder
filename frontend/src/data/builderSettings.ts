import { createDocumentResource } from "frappe-ui/src/resources/documentResource";

const builderSettings = createDocumentResource({
	doctype: "Builder Settings",
	name: "Builder Settings",
	cache: "builderSettings",
	auto: true,
});

export { builderSettings };
