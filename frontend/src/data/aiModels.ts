import type { BuilderAIModel, BuilderAIProvider } from "@/types/doctypes";
import { useLocalStorage } from "@vueuse/core";
import { call, createListResource } from "frappe-ui";

// Providers and models are plain doctypes, so the settings UI talks to them
// directly rather than through builder.ai endpoints — the agent reads the same
// rows server-side (builder/ai/models.py).

export const aiProviders = createListResource({
	doctype: "Builder AI Provider",
	// route_prefix is read-only here: the server derives it, and the model dialog
	// previews the qualified name (<prefix>/<model id>) it will produce.
	// api_key comes back masked, as asterisks: enough to tell whether a key is saved
	fields: [
		"name",
		"provider_name",
		"enabled",
		"route_prefix",
		"litellm_provider",
		"api_base",
		"api_key",
		"from_site_config",
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
		"supports_vision",
		"discovered",
		"frontier_rank",
	],
	orderBy: "frontier_rank asc, creation asc",
	pageLength: 200,
	auto: false,
});

/** the model Bob chats with. Connecting a provider switches it to that provider's best model */
export const selectedAIModel = useLocalStorage("ai-selected-model", "");

export const reloadAIRegistry = async () => {
	await Promise.all([aiProviders.reload(), aiModels.reload()]);
};

// the actions both Bob's /providers menus and Settings take on a provider

export const providerDoc = (name: string): BuilderAIProvider | undefined =>
	(aiProviders.data || []).find((p: BuilderAIProvider) => p.name === name);

export const modelsOf = (provider: string): BuilderAIModel[] =>
	(aiModels.data || []).filter((m: BuilderAIModel) => m.provider === provider);

/** a model discovery retired is gone, not switched off: only the ones someone chose stay listed */
export const listedModelsOf = (provider: string): BuilderAIModel[] =>
	modelsOf(provider).filter((m) => m.enabled || !m.discovered);

export const setProviderEnabled = (name: string, enabled: boolean) =>
	aiProviders.setValue.submit({ name, enabled: enabled ? 1 : 0 });

export const setModelEnabled = (name: string, enabled: boolean) =>
	aiModels.setValue.submit({ name, enabled: enabled ? 1 : 0 });

export const syncProviderModels = (provider: string) => call("builder.ai.api.sync_ai_models", { provider });

export const saveProviderKey = (name: string, apiKey: string) =>
	call("builder.ai.api.save_ai_provider", { provider: { api_key: apiKey }, name });

export const disconnectProvider = (provider: string) =>
	call("builder.ai.api.delete_ai_provider", { provider });
