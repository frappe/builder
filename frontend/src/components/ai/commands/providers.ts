import type { MenuItem, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
import { connectLevel } from "@/components/ai/commands/connect";
import { confirmLevel, creditsFor, creditsLabel, type BobContext } from "@/components/ai/commands/shared";
import { aiModels, aiProviders, reloadAIRegistry } from "@/data/aiModels";
import type { BuilderAIModel, BuilderAIProvider } from "@/types/doctypes";
import { call, toast } from "frappe-ui";

export function providersLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Providers",
		items: async () => {
			// picks up what the gateways added or retired since the picker last asked
			await call("builder.ai.api.sync_ai_models").catch(() => null);
			await reloadAIRegistry();
			const providers: BuilderAIProvider[] = aiProviders.data || [];
			const credits = await creditsFor(providers.filter((p) => p.api_base).map((p) => p.name));
			return [
				...providers.map((p): MenuItem => ({
					key: p.name,
					label: p.provider_name,
					description: p.enabled
						? [modelCount(p.name), creditsLabel(credits[p.name])].filter(Boolean).join(" · ")
						: "Off",
					group: "Connected",
					submenu: true,
					run: () => providerLevel(ctx, p.name),
				})),
				{
					key: "connect",
					label: "Connect a provider",
					icon: "lucide-plus",
					submenu: true,
					run: () => connectLevel(ctx),
				},
			];
		},
	};
}

export function providerLevel(ctx: BobContext, name: string): MenuLevel {
	return {
		title: name,
		items: async () => {
			await reloadAIRegistry();
			return [
				...modelsOf(name).map((m): MenuItem => ({
					key: m.name,
					label: m.label || m.model_id,
					group: "Models",
					switchValue: !!m.enabled,
					run: () => toggleModel(ctx, m),
				})),
				{
					key: "enabled",
					label: "Use this provider",
					switchValue: !!providerDoc(name)?.enabled,
					run: () => toggleProvider(ctx, name),
				},
				{
					key: "key",
					label: "Change API key",
					icon: "lucide-key-round",
					submenu: true,
					run: () => keyLevel(ctx, name),
				},
				{
					key: "delete",
					label: "Delete provider",
					icon: "lucide-trash-2",
					theme: "red",
					submenu: true,
					run: () =>
						confirmLevel(`Delete ${name}?`, `Delete ${name} and its models`, () => remove(ctx, name)),
				},
			];
		},
	};
}

function keyLevel(ctx: BobContext, name: string): MenuLevel {
	return {
		title: "API key",
		input: {
			placeholder: "Paste the new key",
			secret: true,
			submit: async (key): Promise<MenuStep> => {
				if (!key) throw new Error("Paste a key first");
				await call("builder.ai.api.save_ai_provider", { provider: { api_key: key }, name });
				await ctx.refreshAI();
				toast.success("Key saved");
				return "back";
			},
		},
	};
}

async function toggleModel(ctx: BobContext, model: BuilderAIModel): Promise<MenuStep> {
	await aiModels.setValue.submit({ name: model.name, enabled: model.enabled ? 0 : 1 });
	await ctx.refreshAI();
	return "stay";
}

async function toggleProvider(ctx: BobContext, name: string): Promise<MenuStep> {
	await aiProviders.setValue.submit({ name, enabled: providerDoc(name)?.enabled ? 0 : 1 });
	await ctx.refreshAI();
	return "stay";
}

async function remove(ctx: BobContext, name: string): Promise<MenuStep> {
	await call("frappe.client.delete", { doctype: "Builder AI Provider", name });
	await ctx.refreshAI();
	toast.success(`${name} deleted`);
	return { back: 2 };
}

const providerDoc = (name: string): BuilderAIProvider | undefined =>
	(aiProviders.data || []).find((p: BuilderAIProvider) => p.name === name);

const modelsOf = (provider: string): BuilderAIModel[] =>
	(aiModels.data || []).filter((m: BuilderAIModel) => m.provider === provider);

function modelCount(provider: string): string {
	const on = modelsOf(provider).filter((m) => m.enabled).length;
	return on === 1 ? "1 model" : `${on || "no"} models`;
}
