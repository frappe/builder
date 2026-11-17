import type { AIStartOffer } from "@/composables/useAIStart";
import { fp, isMounted } from "@/utils/frappePage";
import { call } from "frappe-ui";
import type { RouteLocationRaw } from "vue-router";

/**
 * frappe.page: a site created from a description (the landing page's "Describe your website", or its onboarding)
 * opens with Bob building the first page from it. The site keeps the description for its owner and names it in their
 * editor boot (fp.start). Onboarding takes it (frappe_page.tenant.start), which holds it for this tab while a page
 * opens and Bob gets the turn: no other tab, reload or member sees it meanwhile, so it runs at most once. Once Bob
 * accepts the turn the site forgets it (done); a start that fails before that gives it back, so a reload offers it
 * again and the user's words are never lost. Nothing of it is kept in the browser.
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
	/** another tab of the user's holds it, and Bob builds there */
	| { kind: "elsewhere" }
	/** the site's AI is off or today's allowance is spent: the description stays on the site for later */
	| { kind: "unavailable" }
	| { kind: "failed"; error: unknown };

/** Why Bob isn't building from the description right now, when it isn't (onboarding's StartDescriptionCard). */
export type StartNotice = { theme: "amber" | "red"; title: string; text: string };

/** Told once whether Bob accepted the first turn (AITurnRequest.settled). */
type Settled = (accepted: boolean) => void;
/** Opens a page with Bob's first turn waiting on it; `settled` hears how that turn went. */
type Start = (description: string, settled: Settled) => Promise<void>;

/** Where the site's copy stands for this tab: not asked for yet (or given back), held here while Bob starts, gone
 * from the site (Bob has it, or the user started another way) though this tab still has the words, or none to take. */
type Hold = "unasked" | "held" | "gone" | "none";

export class PromptStart {
	readonly description = pendingStartDescription();
	private hold: Hold = "unasked";

	get pending() {
		return Boolean(this.description);
	}

	/** Start Bob on the description when the site's AI can take it. */
	begin(offer: AIStartOffer, start: Start): Promise<PromptStartOutcome> {
		if (offer.state !== "ready") return Promise.resolve({ kind: "unavailable" });
		return this.startWith(this.description, start);
	}

	/** Start Bob on `description` (the pending one, maybe edited), holding the site's copy until he accepts it. */
	async startWith(description: string, start: Start): Promise<PromptStartOutcome> {
		try {
			if (!(await this.take())) return { kind: "elsewhere" };
		} catch (error) {
			return { kind: "failed", error };
		}
		const settled = this.settler();
		try {
			await start(description, settled);
			return { kind: "started" };
		} catch (error) {
			// given back before saying so: a retry from here takes it again
			await settled(false);
			return { kind: "failed", error };
		}
	}

	/** The user starts another way: the site forgets the description. */
	async discard() {
		if (this.hold === "gone" || this.hold === "none") return;
		this.hold = "gone";
		delete fp.start;
		await call("frappe_page.tenant.start.done").catch(() => {});
	}

	private async take() {
		if (this.hold === "unasked") {
			const taken = await call<string | null>("frappe_page.tenant.start.take");
			this.hold = taken ? "held" : "none";
			// the home route stops sending the user here
			delete fp.start;
		}
		return this.hold !== "none";
	}

	/** What this start tells the site once Bob accepted the turn or it failed; only the first word counts, and only a
	 * copy this tab holds is the site's to settle. */
	private settler(): (accepted: boolean) => Promise<void> {
		let open = this.hold === "held";
		return async (accepted) => {
			if (!open) return;
			open = false;
			this.hold = accepted ? "gone" : "unasked";
			// a word that never arrives (a closed tab, the site out of reach) the site settles itself (tenant.start)
			await call(`frappe_page.tenant.start.${accepted ? "done" : "give_back"}`).catch(() => {});
		};
	}
}
