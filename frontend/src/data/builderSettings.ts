import { createDocumentResource, frappeRequest, setConfig } from "frappe-ui";
setConfig("resourceFetcher", frappeRequest);

const builderSettings = createDocumentResource({
	doctype: "Builder Settings",
	name: "Builder Settings",
});

export { builderSettings };
