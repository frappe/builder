import { createDocumentResource } from "frappe-ui";

const builderSettings = createDocumentResource({
	doctype: "Builder Settings",
	name: "Builder Settings",
	cache: "builderSettings",
});

export { builderSettings };
