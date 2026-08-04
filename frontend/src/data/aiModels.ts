import { BuilderAIModel, BuilderAIProvider } from "@/types/doctypes";
import { createListResource } from "frappe-ui";

// Providers and models are plain doctypes, so the settings UI talks to them
// directly rather than through builder.ai endpoints — the agent reads the same
// rows server-side (builder/ai/models.py).

export const aiProviders = createListResource({
	doctype: "Builder AI Provider",
	fields: [
		"name",
		"provider_name",
		"enabled",
		"route_prefix",
		"litellm_provider",
		"api_base",
		"extra_headers",
		"extra_body",
	],
	orderBy: "creation asc",
	pageLength: 100,
	auto: false,
});

export const aiModels = createListResource({
	doctype: "Builder AI Model",
	fields: [
		"name",
		"label",
		"provider",
		"model_id",
		"enabled",
		"is_default",
		"is_simple",
		"supports_vision",
		"max_tokens",
		"temperature",
		"input_price",
		"output_price",
	],
	orderBy: "creation asc",
	pageLength: 200,
	auto: false,
});

export const reloadAIRegistry = async () => {
	await Promise.all([aiProviders.reload(), aiModels.reload()]);
};

export const defaultProvider = (): Partial<BuilderAIProvider> => ({
	provider_name: "",
	enabled: 1,
	api_base: "",
});

export const defaultModel = (provider: string): Partial<BuilderAIModel> => ({
	provider,
	model_id: "",
	label: "",
	enabled: 1,
	supports_vision: 0,
	max_tokens: 200000,
});

/** USD per 1M tokens, or "free"/"—" so a price column never reads as a bug. */
export const formatPrice = (value?: number): string => {
	if (value === undefined || value === null) return "—";
	if (!value) return "free";
	return `$${value % 1 === 0 ? value : value.toFixed(2)}`;
};
