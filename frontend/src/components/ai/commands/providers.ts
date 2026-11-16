import type { MenuItem, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
import { catalogLevel } from "@/components/ai/commands/addModel";
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

/** How much of today's AI allowance a site has left, when its host meters the AI that comes with it. */
type Allowance = { percent_left: number; resets_in: string };

export function providersLevel(ctx: BobContext): MenuLevel {
	let allowance: Allowance | null = null;
	return {
		title: "Providers",
		items: withCredits(
			ctx,
			async (): Promise<BuilderAIProvider[]> => {
				// picks up what the gateways added or retired since the picker last asked
				await call("builder.ai.api.sync_ai_models").catch(() => null);
				await reloadAIRegistry();
				allowance = await loadAllowance();
				return aiProviders.data || [];
			},
			// the provider that comes with the site keeps its gateway's address on the server
			(providers) => providers.filter((p) => p.api_base || p.from_site_config).map((p) => p.name),
			(providers, credits) => [
				...providers.map((p): MenuItem => ({
					key: p.name,
					label: p.provider_name,
					description: p.enabled
						? (p.from_site_config
								? ["Included with this site", allowanceLabel(allowance) || modelCount(p.name)]
								: [modelCount(p.name), creditsLabel(credits[p.name])]
							)
								.filter(Boolean)
								.join(" · ")
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
	const included = !!providerDoc(name)?.from_site_config;
	return {
		title: name,
		// the server refuses to change it too: this only keeps the menu from offering what can't be done
		note: included
			? "Comes with this site, so it stays on and can't be removed. You can connect providers of your own alongside it."
			: undefined,
		items: async () => {
			await reloadAIRegistry();
			const models: MenuItem[] = [
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
					key: "add",
					label: "Add a model",
					icon: "lucide-plus",
					submenu: true,
					run: () => catalogLevel(ctx, name),
				},
				{
					key: "refresh",
					label: "Check for new models",
					icon: "lucide-refresh-cw",
					run: () => refreshModels(ctx, name),
				},
			];
			if (included) return [...models, await allowanceItem()].filter((item): item is MenuItem => !!item);
			return [
				...models,
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

async function loadAllowance(): Promise<Allowance | null> {
	return api<Allowance | null>("builder.ai.api.get_site_ai_allowance").catch(() => null);
}

function allowanceLabel(allowance: Allowance | null): string | undefined {
	return allowance ? `${allowance.percent_left}% left today` : undefined;
}

async function allowanceItem(): Promise<MenuItem | null> {
	const allowance = await loadAllowance();
	if (!allowance) return null;
	return {
		key: "allowance",
		label: "Today's allowance",
		description: `${allowance.percent_left}% left · renews at midnight UTC, ${allowance.resets_in}`,
		icon: "lucide-gauge",
		run: () => "stay",
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
