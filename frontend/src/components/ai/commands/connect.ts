import type { CommandMenu, MenuItem, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
import { api, type BobContext, type ImportResult } from "@/components/ai/commands/shared";
import type {
	AIPreset,
	AISetupState,
	BrowserSignIn,
	ConnectResult,
	DeviceSignIn,
	SignInStatus,
} from "@/components/ai/types";
import { toast } from "frappe-ui";

/** Connecting is two steps: pick a provider, then paste its key or approve a ChatGPT
 * sign-in. Nobody picks models here: the server finds the provider's frontier models,
 * and the best of them becomes the one in use. */
export function connectLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Connect a provider",
		items: async () => {
			const state = await api<AISetupState>("builder.ai.api.ai_setup_state");
			if (state.needs_migrate)
				throw new Error("This site is missing Builder's AI tables. Run bench migrate first.");
			return state.presets.map((preset): MenuItem => ({
				key: preset.id,
				label: preset.name || "Other endpoint",
				description: preset.connected ? "Connected" : preset.tagline,
				submenu: true,
				run: () => (preset.oauth ? chatGPTLevel(ctx) : preset.custom ? urlLevel(ctx) : keyLevel(ctx, preset)),
			}));
		},
	};
}

export function keyLevel(ctx: BobContext, preset: AIPreset): MenuLevel {
	return {
		title: preset.name,
		note: preset.connected
			? "Connected. Paste a new key to replace it, or Enter to check for new models."
			: undefined,
		input: {
			placeholder: preset.key_prefix ? `Paste your key (${preset.key_prefix}…)` : "Paste your API key",
			secret: true,
			submit: async (key) => {
				if (!key && !preset.connected) throw new Error("Paste a key first");
				const result = await api<ConnectResult>("builder.ai.api.connect_ai_provider", {
					preset: preset.id,
					api_key: key,
				});
				return connected(ctx, result);
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

/** ChatGPT signs in with a device code: no API key, and nothing redirects back to this
 * site, so it works the same on a hosted site as on a laptop. */
export function chatGPTLevel(ctx: BobContext): MenuLevel {
	let signIn: Promise<DeviceSignIn> | null = null;
	const begin = () => (signIn ??= api<DeviceSignIn>("builder.ai.api.start_codex_login"));
	return {
		title: "ChatGPT",
		note: "Copy the code, then enter it on ChatGPT and approve. Bob connects by itself.",
		items: async () => {
			const login = await begin();
			if (!login.code) throw new Error(login.message || "Could not start the sign-in");
			return [
				{
					key: "code",
					label: login.code,
					description: "Copy code and open ChatGPT",
					icon: "lucide-copy",
					run: () => copyAndOpen(ctx, login),
				},
				{
					key: "browser",
					label: "Sign in with a browser link instead",
					icon: "lucide-external-link",
					submenu: true,
					run: () => browserLevel(ctx),
				},
			];
		},
		start: (menu) => watchDeviceSignIn(ctx, menu, begin),
	};
}

function copyAndOpen(ctx: BobContext, login: DeviceSignIn): MenuStep {
	navigator.clipboard?.writeText(login.code).catch(() => null);
	window.open(login.url, "_blank", "noopener");
	ctx.menu.setNote("Code copied. Paste it on the ChatGPT tab and approve; this finishes by itself.");
	return "stay";
}

/** Polls at the pace OpenAI asked for. Leaving the level stops it; coming back resumes
 * the same code. */
function watchDeviceSignIn(ctx: BobContext, menu: CommandMenu, begin: () => Promise<DeviceSignIn>) {
	let stopped = false;
	let timer: number | undefined;
	const level = menu.level.value;
	const stop = () => {
		stopped = true;
		window.clearTimeout(timer);
	};
	const poll = async (login: DeviceSignIn) => {
		const status = await api<SignInStatus>("builder.ai.api.poll_codex_login", { state: login.state }).catch(
			() => null,
		);
		if (stopped) return;
		if (status?.status === "connected") {
			stop();
			await connected(ctx, status);
			// connecting takes a moment, and a menu opened meanwhile is not ours to close
			if (menu.level.value === level) menu.close();
		} else if (status?.status === "failed" || status?.status === "expired") {
			stop();
			menu.setNote(status.message || "The code expired. Go back and start again.", true);
		} else {
			timer = window.setTimeout(() => poll(login), login.interval * 1000);
		}
	};
	begin()
		.then((login) => {
			if (!stopped && login.state) timer = window.setTimeout(() => poll(login), login.interval * 1000);
		})
		.catch(() => null); // the level's items report it
	return stop;
}

/** The fallback, for a ChatGPT workspace with device codes switched off. The sign-in
 * ends on a localhost page that won't load, and its address finishes the connection. */
function browserLevel(ctx: BobContext): MenuLevel {
	let signIn: Promise<BrowserSignIn> | null = null;
	return {
		title: "Browser sign-in",
		note: "Sign in on the tab that opens. It ends on a page that won't load: copy that page's address and paste it here.",
		input: {
			placeholder: "Paste the address the sign-in ended on",
			submit: async (redirect_url) => {
				const status = await api<SignInStatus>("builder.ai.api.finish_codex_login", { redirect_url });
				if (status.status !== "connected") throw new Error(status.message || "Could not finish the sign-in");
				return connected(ctx, status);
			},
		},
		items: async () => {
			// fetched before the click, so the tab opens inside the click and isn't blocked
			const login = await (signIn ??= api<BrowserSignIn>("builder.ai.api.start_codex_browser_login"));
			return [
				{
					key: "open",
					label: "Open the ChatGPT sign-in",
					icon: "lucide-external-link",
					run: () => openTab(login.url),
				},
			];
		},
	};
}

function urlLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Other endpoint",
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

/** After connecting: let the editor see it, switch to the provider's best model, and say so. */
async function connected(ctx: BobContext, result: ConnectResult): Promise<MenuStep> {
	const best = result.models?.[0];
	if (best) ctx.chat.selectedModel.value = best.name;
	await ctx.refreshAI();
	if (best) toast.success(`${result.provider} connected · using ${best.label}`);
	else toast.warning(`${result.provider} connected, but none of its models suit Bob yet`);
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
