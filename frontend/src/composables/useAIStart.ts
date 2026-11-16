import type { AISetupState } from "@/components/ai/types";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import { isMounted } from "@/utils/frappePage";
import { insertBlankPage } from "@/utils/pageActions";
import { call } from "frappe-ui";
import { ref } from "vue";

/** Whether onboarding offers "Describe your website": not at all, ready, or with today's AI allowance spent. */
export type AIStartOffer = { state: "hidden" } | { state: "ready" } | { state: "spent"; resetsIn: string };

/** Today's allowance of the AI a frappe.page site comes with (builder.ai.api.get_site_ai_allowance). */
type Allowance = { percent_left: number; resets_in: string };

/** The longest description the chat can show as the user's own words (run's display_text). */
export const DESCRIPTION_MAX_LENGTH = 300;

const HIDDEN: AIStartOffer = { state: "hidden" };

/** frappe.page sites only: elsewhere onboarding stays as it was and nothing is asked. */
export async function loadAIStartOffer(): Promise<AIStartOffer> {
	if (!isMounted) return HIDDEN;
	const [setup, allowance] = await Promise.all([
		call<AISetupState>("builder.ai.api.ai_setup_state").catch(() => null),
		call<Allowance | null>("builder.ai.api.get_site_ai_allowance").catch(() => null),
	]);
	if (!setup?.configured) return HIDDEN;
	if (allowance && allowance.percent_left <= 0) return { state: "spent", resetsIn: allowance.resets_in };
	return { state: "ready" };
}

/** What Bob gets for a description, and the line the chat shows for it: the user's own words. A short
 * description leaves most of a page open, which Bob would otherwise ask about before building. */
export function firstMessage(description: string): { prompt: string; display: string } {
	const display = description.trim();
	const prompt = [
		display,
		"This is my new site's first page. Build it now, without asking me anything first: decide what I left open yourself, and keep every name and detail I gave.",
	].join("\n\n");
	return { prompt, display };
}

/** Onboarding's AI start: offered once the site's AI answers, and started on a new page that opens with
 * Bob already building it. */
export function useAIStart() {
	const offer = ref<AIStartOffer>(HIDDEN);
	loadAIStartOffer().then((found) => (offer.value = found));

	async function start(description: string) {
		const page = await insertBlankPage();
		const builderStore = useBuilderStore();
		builderStore.aiTurnRequest = { pageId: page.name, ...firstMessage(description) };
		builderStore.leftPanelActiveTab = "Chat";
		builderStore.showLeftPanel = true;
		await router.push({ name: "builder", params: { pageId: page.name } });
	}

	return { offer, start };
}
