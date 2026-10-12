import { createListResource } from "frappe-ui";

// Providers and models are plain doctypes, so the settings UI talks to them
// directly rather than through builder.ai endpoints — the agent reads the same
// rows server-side (builder/ai/models.py).

export const aiProviders = createListResource({
	doctype: "Builder AI Provider",
	// route_prefix is read-only here: the server derives it, and the model dialog
	// previews the qualified name (<prefix>/<model id>) it will produce.
	fields: ["name", "provider_name", "enabled", "route_prefix", "api_base"],
	orderBy: "creation asc",
	pageLength: 100,
	auto: false,
});

export const aiModels = createListResource({
	doctype: "Builder AI Model",
	fields: ["name", "label", "provider", "model_id", "enabled", "supports_vision"],
	orderBy: "creation asc",
	pageLength: 200,
	auto: false,
});

export const reloadAIRegistry = async () => {
	await Promise.all([aiProviders.reload(), aiModels.reload()]);
};
