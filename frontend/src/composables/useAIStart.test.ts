import { call } from "frappe-ui";
import { beforeEach, describe, expect, it, vi } from "vitest";

const frappePage = vi.hoisted(() => ({ isMounted: true }));
const builderStore = vi.hoisted(() => ({
	aiTurnRequest: null as unknown,
	leftPanelActiveTab: "Layers",
	showLeftPanel: false,
}));
vi.mock("@/utils/frappePage", () => frappePage);
vi.mock("frappe-ui", () => ({ call: vi.fn() }));
vi.mock("@/router", () => ({ default: { push: vi.fn() } }));
vi.mock("@/stores/builderStore", () => ({ default: () => builderStore }));
vi.mock("@/utils/pageActions", () => ({ insertBlankPage: vi.fn() }));

import router from "@/router";
import { insertBlankPage } from "@/utils/pageActions";
import { firstMessage, loadAIStartOffer, useAIStart } from "./useAIStart";

/** What the site's AI answers: whether a model with a key is on offer, and today's allowance. */
function siteAI(configured: boolean, allowance: { percent_left: number; resets_in: string } | null) {
	vi.mocked(call).mockImplementation(async (method: string) => {
		if (method === "builder.ai.api.ai_setup_state") return { configured };
		if (method === "builder.ai.api.get_site_ai_allowance") return allowance;
		throw new Error(`unexpected call ${method}`);
	});
}

beforeEach(() => {
	frappePage.isMounted = true;
	vi.mocked(call).mockReset();
	vi.mocked(router.push).mockReset().mockResolvedValue(undefined);
	vi.mocked(insertBlankPage).mockReset();
	Object.assign(builderStore, { aiTurnRequest: null, leftPanelActiveTab: "Layers", showLeftPanel: false });
});

describe("the AI start offer", () => {
	it("is hidden on a site frappe.page doesn't host, without asking anything", async () => {
		frappePage.isMounted = false;
		expect(await loadAIStartOffer()).toEqual({ state: "hidden" });
		expect(call).not.toHaveBeenCalled();
	});

	it("is hidden when the site has no AI with a key", async () => {
		siteAI(false, null);
		expect(await loadAIStartOffer()).toEqual({ state: "hidden" });
	});

	it("is hidden when the site's AI can't be asked", async () => {
		vi.mocked(call).mockRejectedValue(new Error("offline"));
		expect(await loadAIStartOffer()).toEqual({ state: "hidden" });
	});

	it("is ready while some of today's allowance is left", async () => {
		siteAI(true, { percent_left: 1, resets_in: "in about 2 hours" });
		expect(await loadAIStartOffer()).toEqual({ state: "ready" });
	});

	it("is ready when nothing meters the site's AI", async () => {
		siteAI(true, null);
		expect(await loadAIStartOffer()).toEqual({ state: "ready" });
	});

	it("says when the allowance renews once today's is spent", async () => {
		siteAI(true, { percent_left: 0, resets_in: "in about 2 hours" });
		expect(await loadAIStartOffer()).toEqual({ state: "spent", resetsIn: "in about 2 hours" });
	});
});

describe("the first message", () => {
	it("shows the user's own words and leaves Bob free to ask what the description left open", () => {
		const { prompt, display } = firstMessage("  A bakery in Pune called Crumb.  ");
		expect(display).toBe("A bakery in Pune called Crumb.");
		expect(prompt).toBe("A bakery in Pune called Crumb.\n\nThis is my new site's first page.");
	});
});

describe("the offer onboarding waits on", () => {
	it("resolves with what the offer settled on, so a start from a carried description can wait for it", async () => {
		siteAI(true, { percent_left: 0, resets_in: "in about 2 hours" });
		const { offer, loaded } = useAIStart();
		expect(await loaded).toEqual({ state: "spent", resetsIn: "in about 2 hours" });
		expect(offer.value).toEqual({ state: "spent", resetsIn: "in about 2 hours" });
	});
});

describe("starting from a description", () => {
	it("opens a new page with Bob's chat showing and the turn waiting for that page", async () => {
		siteAI(true, null);
		vi.mocked(insertBlankPage).mockResolvedValue({ name: "page-1" } as never);
		const { start } = useAIStart();
		await start("A bakery in Pune called Crumb.");
		expect(builderStore.aiTurnRequest).toEqual({
			pageId: "page-1",
			...firstMessage("A bakery in Pune called Crumb."),
		});
		expect(builderStore.leftPanelActiveTab).toBe("Chat");
		expect(builderStore.showLeftPanel).toBe(true);
		expect(router.push).toHaveBeenCalledWith({ name: "builder", params: { pageId: "page-1" } });
	});

	it("lets the screen that asked hear whether Bob accepted the turn", async () => {
		siteAI(true, null);
		vi.mocked(insertBlankPage).mockResolvedValue({ name: "page-1" } as never);
		const settled = vi.fn();
		await useAIStart().start("A bakery in Pune called Crumb.", settled);
		expect(builderStore.aiTurnRequest).toMatchObject({ pageId: "page-1", settled });
	});

	it("asks Bob for nothing when the page can't be made", async () => {
		siteAI(true, null);
		vi.mocked(insertBlankPage).mockRejectedValue(new Error("no permission"));
		const { start } = useAIStart();
		await expect(start("A bakery")).rejects.toThrow("no permission");
		expect(builderStore.aiTurnRequest).toBeNull();
		expect(router.push).not.toHaveBeenCalled();
	});
});
