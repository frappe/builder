import type { MenuItem, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
import { chatGPTLevel, connectLevel, keyLevel as presetKeyLevel } from "@/components/ai/commands/connect";
import {
	api,
	confirmLevel,
	creditsLabel,
	withCredits,
	type BobContext,
} from "@/components/ai/commands/shared";
import type { AISetupState } from "@/components/ai/types";
import { aiModels, aiProviders, reloadAIRegistry } from "@/data/aiModels";
import type { BuilderAIModel, BuilderAIProvider } from "@/types/doctypes";
import { call, toast } from "frappe-ui";

export function providersLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Providers",
		items: withCredits(
			ctx,
			async (): Promise<BuilderAIProvider[]> => {
				// picks up what the gateways added or retired since the picker last asked
				await call("builder.ai.api.sync_ai_models").catch(() => null);
				await reloadAIRegistry();
				return aiProviders.data || [];
			},
			(providers) => providers.filter((p) => p.api_base).map((p) => p.name),
			(providers, credits) => [
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
			],
		),
	};
}

export function providerLevel(ctx: BobContext, name: string): MenuLevel {
	return {
		title: name,
		items: async () => {
			await reloadAIRegistry();
			return [
				// a model discovery retired is gone, not switched off: only the ones someone chose stay listed
				...modelsOf(name)
					.filter((m) => m.enabled || !m.discovered)
					.map((m): MenuItem => ({
						key: m.name,
						label: m.label || m.model_id,
						group: "Models",
						switchValue: !!m.enabled,
						run: () => toggleModel(ctx, m),
					})),
				{
					key: "refresh",
					label: "Check for new models",
					icon: "lucide-refresh-cw",
					run: () => refreshModels(ctx, name),
				},
				{
					key: "enabled",
					label: "Use this provider",
					icon: "lucide-power",
					switchValue: !!providerDoc(name)?.enabled,
					run: () => toggleProvider(ctx, name),
				},
				credentialItem(ctx, name),
				{
					key: "delete",
					label: "Disconnect",
					icon: "lucide-unplug",
					theme: "red",
					submenu: true,
					run: () =>
						confirmLevel(`Disconnect ${name}?`, `Disconnect ${name} and remove its models`, () =>
							remove(ctx, name),
						),
				},
			];
		},
	};
}

/** A ChatGPT sign-in is renewed by signing in again; a key goes through the same check as connecting. */
function credentialItem(ctx: BobContext, name: string): MenuItem {
	const provider = providerDoc(name);
	if (provider?.litellm_provider === "codex")
		return {
			key: "signin",
			label: "Sign in again",
			icon: "lucide-log-in",
			submenu: true,
			run: () => chatGPTLevel(ctx),
		};
	return {
		key: "key",
		label: "Change API key",
		icon: "lucide-key-round",
		submenu: true,
		run: async () => {
			if (provider?.api_base) return keyLevel(ctx, name);
			const state = await api<AISetupState>("builder.ai.api.ai_setup_state");
			const preset = state.presets.find((p) => p.name === name);
			return preset ? presetKeyLevel(ctx, preset) : keyLevel(ctx, name);
		},
	};
}

async function refreshModels(ctx: BobContext, name: string): Promise<MenuStep> {
	const before = modelsOf(name).filter((m) => m.enabled).length;
	await call("builder.ai.api.sync_ai_models", { provider: name });
	await ctx.refreshAI();
	await reloadAIRegistry();
	const after = modelsOf(name).filter((m) => m.enabled).length;
	toast.success(after === before ? "Up to date" : `${name} now offers ${modelCount(name)}`);
	return "stay";
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
	await call("builder.ai.api.delete_ai_provider", { provider: name });
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
