import { createListResource } from "frappe-ui";

import useStore from "@/store";
import Block from "@/utils/block";
const store = useStore();

const webComponent = createListResource({
	method: "GET",
	doctype: "Web Page Component",
	fields: ["component_name", "icon", "block", "name"],
	orderBy: "creation",
	cache: "components",
	start: 0,
	pageLength: 100,
	auto: true,
	transform(data: any[]) {
		data.forEach((d) => {
			if (!(d.block instanceof Block)) {
				d.block = new Block(store.getBlockCopy(JSON.parse(d.block)));
			}
		});
		return data;
	},
});

export default webComponent;
