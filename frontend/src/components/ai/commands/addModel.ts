import type { MenuItem, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
import { api, type BobContext } from "@/components/ai/commands/shared";
import type { AddableModel } from "@/components/ai/types";
import { toast } from "frappe-ui";

/** The picker offers a provider's frontier; this row reaches everything else it serves,
 * like an open-weights model. Pinned, so typing a name the picker doesn't know still
 * leaves a way to add it, and the typed name carries over as the filter. */
export function addModelItem(ctx: BobContext, providers: string[]): MenuItem {
	return {
		key: "add-model",
		label: "Add a model",
		icon: "lucide-plus",
		submenu: true,
		pinned: true,
		run: () => {
			const query = ctx.chat.prompt.value.trim();
			return providers.length === 1
				? catalogLevel(ctx, providers[0], query)
				: providerChoiceLevel(ctx, providers, query);
		},
	};
}

function providerChoiceLevel(ctx: BobContext, providers: string[], query: string): MenuLevel {
	return {
		title: "Add a model from",
		items: () =>
			providers.map((provider) => ({
				key: provider,
				label: provider,
				submenu: true,
				run: () => catalogLevel(ctx, provider, query),
			})),
	};
}

/** Everything the provider serves that the picker doesn't offer, newest first. */
export function catalogLevel(ctx: BobContext, provider: string, query = ""): MenuLevel {
	return {
		title: `Add from ${provider}`,
		query,
		empty: `Nothing else on ${provider} can drive Bob.`,
		items: async () => {
			const models = await api<AddableModel[]>("builder.ai.api.get_addable_models", { provider });
			return models.map((model) => ({
				key: model.model_id,
				label: model.label,
				description: describe(model),
				run: () => add(ctx, provider, model),
			}));
		},
	};
}

async function add(ctx: BobContext, provider: string, model: AddableModel): Promise<MenuStep> {
	const added = await api<{ name: string; label: string }>("builder.ai.api.add_ai_model", {
		provider,
		model_id: model.model_id,
	});
	ctx.chat.selectedModel.value = added.name;
	await ctx.refreshAI();
	toast.success(`Added ${added.label}`);
}

function describe(model: AddableModel): string {
	const parts = [model.model_id];
	if (model.released)
		parts.push(new Date(model.released).toLocaleDateString(undefined, { month: "short", year: "numeric" }));
	if (model.context) parts.push(`${tokens(model.context)} context`);
	if (model.vision === false) parts.push("no images");
	return parts.join(" · ");
}

function tokens(count: number): string {
	return count >= 1_000_000 ? `${+(count / 1_000_000).toFixed(1)}M` : `${Math.round(count / 1000)}K`;
}
