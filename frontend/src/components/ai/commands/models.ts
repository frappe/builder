import type { MenuItem, MenuLevel } from "@/components/ai/commandMenu";
import { addModelItem } from "@/components/ai/commands/addModel";
import { api, creditsLabel, withCredits, type BobContext } from "@/components/ai/commands/shared";
import type { AIProvider } from "@/components/ai/types";

const EFFORT_LABELS: Record<string, string> = {
	low: "Light",
	medium: "Medium",
	high: "High",
	xhigh: "Extra High",
	max: "Max",
};

export function modelSettingsLevel(ctx: BobContext): MenuLevel {
	return {
		title: "AI settings",
		items: async () => {
			if (!ctx.chat.availableModels.value.length) await loadGroups(ctx);
			return [
				{
					key: "fast",
					label: "Fast",
					description: ctx.chat.fastSupported.value
						? "Faster processing at a higher API price"
						: "Available for direct OpenAI API models",
					switchValue: ctx.chat.fastEnabled.value,
					disabled: !ctx.chat.fastSupported.value,
					run: () => {
						ctx.chat.toggleFast();
						return "stay";
					},
				},
				{
					key: "reasoning",
					label: "Reasoning",
					description: EFFORT_LABELS[ctx.chat.reasoningEffort.value] || "Unavailable for this model",
					submenu: !!ctx.chat.reasoningEfforts.value.length,
					disabled: !ctx.chat.reasoningEfforts.value.length,
					run: () => reasoningLevel(ctx),
				},
				{
					key: "model",
					label: "Model",
					description: ctx.chat.modelLabel.value,
					submenu: true,
					run: () => modelLevel(ctx),
				},
			];
		},
	};
}

function reasoningLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Reasoning",
		items: () =>
			ctx.chat.reasoningEfforts.value.map((effort) => ({
				key: effort,
				label: EFFORT_LABELS[effort] || effort,
				description: effort === "high" ? "Default" : undefined,
				selected: ctx.chat.reasoningEffort.value === effort,
				run: () => {
					ctx.chat.setReasoningEffort(effort);
					return "back";
				},
			})),
	};
}

export function modelLevel(ctx: BobContext, query = ""): MenuLevel {
	return {
		title: "Model",
		query,
		empty: "No models yet. Connect one with /providers.",
		items: withCredits(
			ctx,
			() => loadGroups(ctx),
			(groups) => groups.filter((g) => g.models.some((m) => m.api_base)).map((g) => g.provider),
			(groups, credits) => [
				...groups.flatMap((group) =>
					group.models.map((model): MenuItem => ({
						key: model.name,
						label: model.label,
						description: model.ready === false ? "No API key" : undefined,
						group: [group.provider, creditsLabel(credits[group.provider])].filter(Boolean).join(" · "),
						selected: model.name === ctx.chat.selectedModel.value,
						run: () => {
							ctx.chat.selectedModel.value = model.name;
						},
					})),
				),
				...(groups.length
					? [
							addModelItem(
								ctx,
								groups.map((g) => g.provider),
							),
						]
					: []),
			],
		),
	};
}

/** The picker's providers, fetched fresh: a gateway adds and retires models without notice. */
async function loadGroups(ctx: BobContext): Promise<AIProvider[]> {
	const groups = (await api<AIProvider[]>("builder.ai.api.get_ai_models")) || [];
	ctx.chat.availableModels.value = groups;
	return groups;
}
