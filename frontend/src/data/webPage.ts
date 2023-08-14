import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import { createListResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Web Page Beta",
	fields: ["name", "route", "blocks", "page_name", "preview", "page_title", "creation", "page_data"],
	auto: true,
	cache: "pages",
	orderBy: "creation desc",
	pageLength: 50,
	transform: (data: WebPageBeta[]) => {
		data.forEach((d) => {
			try {
				d.page_data = JSON.parse(d.page_data || "{}");
			} catch (e) {
				//
			}
		});
	},
});

export { webPages };
