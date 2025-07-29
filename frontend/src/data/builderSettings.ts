import { frappeRequest, setConfig } from "frappe-ui";
import { createDocumentResource } from "frappe-ui/src/resources/documentResource";
setConfig("resourceFetcher", frappeRequest);

const builderSettings = createDocumentResource({
	doctype: "Builder Settings",
	name: "Builder Settings",
});

export { builderSettings };
