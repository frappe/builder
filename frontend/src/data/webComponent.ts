import { createListResource } from "frappe-ui";

import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import Block from "@/utils/block";
import { reactive } from "vue";

const webComponent = createListResource({
	method: "GET",
	doctype: "Builder Component",
	fields: ["component_name", "block", "name", "for_web_page", "component_id"],
	orderBy: "creation",
	cache: "components",
	start: 0,
	pageLength: 100,
	auto: true,
	transform(data: BuilderComponent[]) {
		data.forEach((d) => {
			if (!(d.block instanceof Block)) {
				d.block = reactive(new Block(JSON.parse(d.block)));
			}
		});
		return data;
	},
});

export default webComponent;
