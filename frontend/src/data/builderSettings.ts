import useStore from "@/store";
import { createDocumentResource } from "frappe-ui";
const store = useStore();

const builderSettings = createDocumentResource({
	doctype: "Builder Settings",
	name: "Builder Settings",
	cache: "builderSettings",
	auto: store.isTrialMode,
});

export { builderSettings };
