import type { CommandMenu, MenuItem, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
import {
	api,
	type BobContext,
	type ImportResult,
	type KeyCheck,
	type SignInStart,
	type SignInStatus,
} from "@/components/ai/commands/shared";
import type { AIPreset, AISetupState } from "@/components/ai/types";
import { getErrorMessage } from "@/utils/helpers";
import { toast } from "frappe-ui";

export function connectLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Connect",
		items: async () => {
			const state = await api<AISetupState>("builder.ai.api.ai_setup_state");
			if (state.needs_migrate)
				throw new Error("This site is missing Builder's AI tables. Run bench migrate first.");
			return state.presets.map((preset): MenuItem => ({
				key: preset.id,
				label: preset.name || "Custom endpoint",
				description: preset.configured ? "Connected" : preset.tagline,
				submenu: true,
				run: () =>
					preset.oauth ? signInLevel(ctx, preset) : preset.custom ? urlLevel(ctx) : keyLevel(ctx, preset),
			}));
		},
	};
}

function keyLevel(ctx: BobContext, preset: AIPreset): MenuLevel {
	return {
		title: preset.name,
		note: preset.has_key ? "Leave it blank to keep the stored key." : undefined,
		input: {
			placeholder: preset.key_prefix ? `${preset.key_prefix}…` : "API key",
			secret: true,
			submit: async (key) => {
				if (!key && !preset.has_key) throw new Error("Paste a key first");
				const check = await api<KeyCheck>("builder.ai.api.verify_ai_key", {
					preset: preset.id,
					api_key: key,
				});
				// "warn" is a good key on an account that needs attention elsewhere, like credit
				if (!check.success && check.severity === "error") throw new Error(check.message);
				return install(ctx, preset, { api_key: key });
			},
		},
		items: () =>
			preset.key_url
				? [
						{
							key: "get",
							label: `Get a key at ${new URL(preset.key_url).host}`,
							icon: "lucide-external-link",
							run: () => openTab(preset.key_url),
						},
					]
				: [],
	};
}

function urlLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Custom endpoint",
		input: {
			placeholder: "Base URL, like http://localhost:11434/v1",
			submit: (url) => {
				if (!/^https?:\/\/\S+$/.test(url)) throw new Error("That doesn't look like a URL");
				return endpointKeyLevel(ctx, url.replace(/\/+$/, ""));
			},
		},
	};
}

function endpointKeyLevel(ctx: BobContext, url: string): MenuLevel {
	return {
		title: new URL(url).host,
		input: {
			placeholder: "API key, or Enter if it needs none",
			secret: true,
			submit: async (key) => {
				const provider = await api<string>("builder.ai.api.save_ai_provider", {
					provider: { provider_name: nameFromUrl(url), api_base: url, api_key: key, enabled: 1 },
				});
				const imported = await api<ImportResult>("builder.ai.api.import_provider_models", { provider });
				await ctx.refreshAI();
				toast.success(`${provider} connected with ${imported.added.length} models`);
			},
		},
	};
}

function signInLevel(ctx: BobContext, preset: AIPreset): MenuLevel {
	return {
		title: preset.name,
		note: "Opening the sign-in…",
		input: {
			placeholder: "Or paste the redirect URL here",
			submit: async (redirect_url) => {
				const res = await api<SignInStatus>("builder.ai.api.finish_codex_login", { redirect_url });
				if (res.status !== "connected") throw new Error(res.message || "Could not finish the sign-in");
				return install(ctx, preset);
			},
		},
		start: (menu) => watchSignIn(ctx, preset, menu),
	};
}

function watchSignIn(ctx: BobContext, preset: AIPreset, menu: CommandMenu) {
	let timer: number | undefined;
	api<SignInStart>("builder.ai.api.start_codex_login")
		.then((login) => {
			window.open(login.url, "_blank", "noopener");
			menu.setNote("Finish signing in on the tab that opened. This carries on by itself.");
			timer = window.setInterval(async () => {
				const poll = await api<SignInStatus>("builder.ai.api.poll_codex_login", { state: login.state }).catch(
					() => null,
				);
				if (poll?.status === "connected") {
					window.clearInterval(timer);
					await install(ctx, preset);
					menu.close();
				} else if (poll?.status === "failed" || poll?.status === "expired") {
					window.clearInterval(timer);
					menu.setNote(poll.message || "The sign-in didn't finish. Go back and try again.", true);
				}
			}, 2500);
		})
		.catch((error: unknown) => menu.setNote(getErrorMessage(error, "Could not start the sign-in"), true));
	return () => window.clearInterval(timer);
}

/** Connects with the preset's recommended models; the rest can be switched on from /providers. */
async function install(
	ctx: BobContext,
	preset: AIPreset,
	fields: { api_key?: string } = {},
): Promise<MenuStep> {
	const models = preset.models.filter((m) => m.recommended).map((m) => m.model_id);
	const res = await api<{ provider: string }>("builder.ai.api.setup_ai_provider", {
		preset: preset.id,
		api_key: fields.api_key || "",
		// JSON, not a bare array: form encoding keeps only the first value
		models: JSON.stringify(models),
	});
	await ctx.refreshAI();
	toast.success(`${res.provider} connected`);
}

function openTab(url: string): MenuStep {
	window.open(url, "_blank", "noopener");
	return "stay";
}

function nameFromUrl(url: string): string {
	const { hostname } = new URL(url);
	const label = hostname.split(".").find((part) => !["api", "www", "gateway"].includes(part)) || hostname;
	return /^\d/.test(label) ? hostname : label[0].toUpperCase() + label.slice(1);
}
