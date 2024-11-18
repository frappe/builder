import useStore from "@/store";
import { createDocumentResource } from "frappe-ui";

const store = useStore();

const websiteSettings = createDocumentResource({
	doctype: "Website Settings",
	name: "Website Settings",
	auto: !store.isDemoMode,
});

export { websiteSettings };
