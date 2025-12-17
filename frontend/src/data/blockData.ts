import { createResource } from "frappe-ui";

let fetchBlockData = createResource({
	url: "builder.builder.doctype.builder_page.builder_page.get_block_data",
	method: "GET",
	auto: false,
});

export default fetchBlockData;
