import type { MenuItem, MenuLevel } from "@/components/ai/commandMenu";
import { api, creditsFor, creditsLabel, type BobContext } from "@/components/ai/commands/shared";
import type { AIProvider } from "@/components/ai/types";

export function modelLevel(ctx: BobContext, query = ""): MenuLevel {
	return {
		title: "Model",
		query,
		empty: "No models yet. Connect one with /providers.",
		items: async () => {
			const { groups, credits } = await loadProviders(ctx);
			return groups.flatMap((group) =>
				group.models.map((model): MenuItem => ({
					key: model.name,
					label: model.label,
					hint: model.ready === false ? "no API key" : undefined,
					group: [group.provider, creditsLabel(credits[group.provider])].filter(Boolean).join(" · "),
					checked: model.name === ctx.chat.selectedModel.value,
					run: () => {
						ctx.chat.selectedModel.value = model.name;
					},
				})),
			);
		},
	};
}

/** The picker's providers, fetched fresh: a gateway adds and retires models without notice. */
async function loadProviders(ctx: BobContext) {
	const groups = (await api<AIProvider[]>("builder.ai.api.get_ai_models")) || [];
	ctx.chat.availableModels.value = groups;
	const reporting = groups.filter((g) => g.models.some((m) => m.api_base)).map((g) => g.provider);
	return { groups, credits: await creditsFor(reporting) };
}
