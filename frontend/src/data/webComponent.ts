import { createListResource } from "frappe-ui";

import useStore from "@/store";
import Block from "@/utils/block";

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
		const store = useStore();
		data.forEach((d) => {
			if (!(d.block instanceof Block)) {
				d.block = new Block(store.getBlockCopy(JSON.parse(d.block)));
			}
		});
		return data;
	},
});

export default webComponent;
