import type { AIStartOffer } from "@/composables/useAIStart";
import { fp, isMounted } from "@/utils/frappePage";
import { call } from "frappe-ui";
import type { RouteLocationRaw } from "vue-router";

/**
 * frappe.page: a site created from a description (the landing page's "Describe your website", or its onboarding)
 * opens with Bob building the first page from it. The site keeps the description for its owner and names it in their
 * editor boot (fp.start) until onboarding takes it (frappe_page.tenant.start.take), which deletes it there: it runs
 * at most once, in one tab, and never for another member or account. Nothing of it is kept in the browser.
 */

/** The description this editor still has to start from, or "". */
export function pendingStartDescription(): string {
	return (isMounted && fp.start?.description) || "";
}

/** The home route sends an owner with a description to onboarding, which starts Bob on it at once. */
export function promptStartRedirect(): RouteLocationRaw | undefined {
	return pendingStartDescription() ? { name: "persona-survey" } : undefined;
}

export type PromptStartOutcome =
	| { kind: "started" }
	/** another tab of the user's took it first, and Bob builds there */
	| { kind: "elsewhere" }
	/** the site's AI is off or today's allowance is spent: the description stays on the site for later */
	| { kind: "unavailable" }
	| { kind: "failed"; error: unknown };

/** Why Bob isn't building from the description right now, when it isn't (onboarding's StartDescriptionCard). */
export type StartNotice = { theme: "amber" | "red"; title: string; text: string };

type Start = (description: string) => Promise<void>;

export class PromptStart {
	readonly description = pendingStartDescription();
	/** what the site handed over: null until asked, "" when there was nothing left to take */
	private taken: string | null = null;

	get pending() {
		return Boolean(this.description);
	}

	/** Start Bob on the description when the site's AI can take it. */
	begin(offer: AIStartOffer, start: Start): Promise<PromptStartOutcome> {
		if (offer.state !== "ready") return Promise.resolve({ kind: "unavailable" });
		return this.startWith(this.description, start);
	}

	/** Start Bob on `description` (the pending one, maybe edited), once the site has handed the pending one over. */
	async startWith(description: string, start: Start): Promise<PromptStartOutcome> {
		try {
			if (!(await this.take())) return { kind: "elsewhere" };
			await start(description);
			return { kind: "started" };
		} catch (error) {
			return { kind: "failed", error };
		}
	}

	/** The user starts another way: the site forgets the description. */
	async discard() {
		await this.take().catch(() => false);
	}

	private async take() {
		if (this.taken === null) {
			this.taken = (await call<string | null>("frappe_page.tenant.start.take")) || "";
			// the home route stops sending the user here
			delete fp.start;
		}
		return Boolean(this.taken);
	}
}
