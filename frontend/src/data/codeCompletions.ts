import { createResource } from "frappe-ui";

let codeCompletions = createResource({
	url: "builder.api.get_codemirror_completions",
	method: "GET",
	auto: true,
});

export default codeCompletions;
