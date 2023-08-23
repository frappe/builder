import { createListResource } from "frappe-ui";

import Block from "@/utils/block";
import { reactive } from "vue";

const webComponent = createListResource({
	method: "GET",
	doctype: "Web Page Component",
	fields: ["component_name", "block", "name", "for_web_page"],
	orderBy: "creation",
	cache: "components",
	start: 0,
	pageLength: 100,
	auto: true,
	transform(data: any[]) {
		data.forEach((d) => {
			if (!(d.block instanceof Block)) {
				d.block = reactive(new Block(JSON.parse(d.block)));
			}
		});
		return data;
	},
});

export default webComponent;
