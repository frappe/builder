import { createListResource } from "frappe-ui";

import useStore from "@/store";
import { reactive } from "vue";
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
			d.block = reactive(store.getBlockCopy(JSON.parse(d.block)));
			d.block.isComponent = true;
			d.block.blockName = d.block.blockName || d.component_name;
		});
		return data;
	},
});

export default webComponent;
