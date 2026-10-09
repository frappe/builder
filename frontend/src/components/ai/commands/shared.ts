import type { AIChatController } from "@/components/AIChatController";
import type { CommandMenu, MenuLevel, MenuStep } from "@/components/ai/commandMenu";
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

export function creditsLabel(credits: Credits | null | undefined): string | undefined {
	return credits ? `${money(credits.balance)} left` : undefined;
}

export function confirmLevel(title: string, label: string, action: () => Promise<MenuStep>): MenuLevel {
	return {
		title,
		items: () => [
			{ key: "confirm", label, icon: "lucide-trash-2", danger: true, run: action },
			{ key: "cancel", label: "Cancel", icon: "lucide-x", run: () => "back" },
		],
	};
}
