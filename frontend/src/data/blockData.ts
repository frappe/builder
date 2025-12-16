import { createResource } from "frappe-ui";

let getBlockData = createResource({
	url: "builder.builder.doctype.builder_page.builder_page.get_block_data",
	method: "GET",
	auto: false,
});

export default getBlockData;
