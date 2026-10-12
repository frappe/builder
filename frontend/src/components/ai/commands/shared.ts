import type { AIChatController } from "@/components/AIChatController";
import type { CommandMenu, MenuItem, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
import { call } from "frappe-ui";

/** What a command can reach: the chat it belongs to, the menu showing it, and a way to
 * make the rest of the editor see provider and model changes. */
export type BobContext = {
	chat: AIChatController;
	menu: CommandMenu;
	refreshAI: () => Promise<void>;
};

export type Credits = { balance: number; spent: number | null };
export type KeyCheck = { success: boolean; severity: "ok" | "warn" | "error"; message: string };
export type ImportResult = { added: string[]; skipped: string[]; found: number };
export type SignInStart = { url: string; state: string };
export type SignInStatus = { status: "pending" | "connected" | "failed" | "expired"; message?: string };

/** frappe-ui's call() resolves to unknown; this is the one place a response gets its shape. */
export const api = <T>(method: string, params?: Record<string, unknown>) =>
	call(method, params) as Promise<T>;

const money = (value: number) => `$${value.toFixed(2)}`;

/** Balances for the providers that report one, keyed by provider. One failing never hides the rest. */
export async function creditsFor(providers: string[]): Promise<Record<string, Credits | null>> {
	const entries = await Promise.all(
		providers.map(async (provider) => {
			const credits = await api<Credits | null>("builder.ai.api.get_provider_credits", { provider }).catch(
				() => null,
			);
			return [provider, credits ?? null] as const;
		}),
	);
	return Object.fromEntries(entries);
}

/** A level's items with balances added once they arrive: a gateway slow to answer /credits
 * must not hold up the list. The redraw reuses the data `load` fetched rather than asking again. */
export function withCredits<T>(
	ctx: BobContext,
	load: () => Promise<T>,
	providersOf: (data: T) => string[],
	build: (data: T, credits: Record<string, Credits | null>) => MenuItem[],
): () => Promise<MenuItem[]> {
	let data: T;
	let reuse = false;
	let asked = false;
	let credits: Record<string, Credits | null> = {};
	return async () => {
		if (!reuse) data = await load();
		reuse = false;
		if (!asked) {
			asked = true;
			const level = ctx.menu.level.value;
			creditsFor(providersOf(data)).then((found) => {
				credits = found;
				if (ctx.menu.level.value !== level) return;
				reuse = true;
				ctx.menu.reload();
			});
		}
		return build(data, credits);
	};
}

export function creditsLabel(credits: Credits | null | undefined): string | undefined {
	return credits ? `${money(credits.balance)} left` : undefined;
}

export function confirmLevel(title: string, label: string, action: () => Promise<MenuStep>): MenuLevel {
	return {
		title,
		items: () => [
			{ key: "confirm", label, icon: "lucide-trash-2", theme: "red", run: action },
			{ key: "cancel", label: "Cancel", icon: "lucide-x", run: () => "back" },
		],
	};
}
