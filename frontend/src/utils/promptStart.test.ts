import { call } from "frappe-ui";
import { beforeEach, describe, expect, it, vi } from "vitest";

const frappePage = vi.hoisted(() => ({
	isMounted: true,
	fp: {} as { start?: { description: string } },
}));
vi.mock("@/utils/frappePage", () => frappePage);
vi.mock("frappe-ui", () => ({ call: vi.fn() }));

import { PromptStart, pendingStartDescription, promptStartRedirect } from "./promptStart";

const DESCRIPTION = "A bakery in Pune called Crumb.";
const READY = { state: "ready" } as const;

/** The site's copy: take() hands it over once, then there is none. */
function siteKeeps(description: string | null) {
	let kept = description;
	vi.mocked(call).mockImplementation(async (method: string) => {
		if (method !== "frappe_page.tenant.start.take") throw new Error(`unexpected call ${method}`);
		const taken = kept;
		kept = null;
		return taken;
	});
}

beforeEach(() => {
	frappePage.isMounted = true;
	frappePage.fp = { start: { description: DESCRIPTION } };
	vi.mocked(call).mockReset();
	siteKeeps(DESCRIPTION);
});

describe("the pending description", () => {
	it("is the one the owner's editor boot names", () => {
		expect(pendingStartDescription()).toBe(DESCRIPTION);
		expect(promptStartRedirect()).toEqual({ name: "persona-survey" });
	});

	it("is none for anyone the boot names none for, and the dashboard opens as usual", () => {
		frappePage.fp = {};
		expect(pendingStartDescription()).toBe("");
		expect(promptStartRedirect()).toBeUndefined();
		expect(new PromptStart().pending).toBe(false);
	});

	it("is none off frappe.page, whatever the boot says", () => {
		frappePage.isMounted = false;
		expect(pendingStartDescription()).toBe("");
		expect(promptStartRedirect()).toBeUndefined();
	});
});

describe("starting Bob on it", () => {
	it("takes it from the site, then starts Bob on it", async () => {
		const start = vi.fn().mockResolvedValue(undefined);
		const outcome = await new PromptStart().begin(READY, start);
		expect(outcome).toEqual({ kind: "started" });
		expect(call).toHaveBeenCalledWith("frappe_page.tenant.start.take");
		expect(start).toHaveBeenCalledWith(DESCRIPTION);
	});

	it("runs once: after it is taken, a reload's boot names none and the home route stays", async () => {
		await new PromptStart().begin(READY, vi.fn().mockResolvedValue(undefined));
		expect(frappePage.fp.start).toBeUndefined();
		expect(promptStartRedirect()).toBeUndefined();
	});

	it("starts nothing when another tab took it first", async () => {
		siteKeeps(null);
		const start = vi.fn();
		expect(await new PromptStart().begin(READY, start)).toEqual({ kind: "elsewhere" });
		expect(start).not.toHaveBeenCalled();
	});

	it("leaves it on the site while the AI can't take it", async () => {
		const start = vi.fn();
		const spent = { state: "spent", resetsIn: "in 2 hours" } as const;
		expect(await new PromptStart().begin(spent, start)).toEqual({ kind: "unavailable" });
		expect(await new PromptStart().begin({ state: "hidden" }, start)).toEqual({ kind: "unavailable" });
		expect(call).not.toHaveBeenCalled();
		expect(start).not.toHaveBeenCalled();
		expect(frappePage.fp.start).toEqual({ description: DESCRIPTION });
	});

	it("starts again from what it took when opening the page failed, without taking twice", async () => {
		const promptStart = new PromptStart();
		const failing = vi.fn().mockRejectedValue(new Error("no permission"));
		const outcome = await promptStart.begin(READY, failing);
		expect(outcome).toMatchObject({ kind: "failed" });

		const start = vi.fn().mockResolvedValue(undefined);
		expect(await promptStart.startWith("A bakery called Crumb, in Pune.", start)).toEqual({
			kind: "started",
		});
		expect(start).toHaveBeenCalledWith("A bakery called Crumb, in Pune.");
		expect(call).toHaveBeenCalledTimes(1);
	});

	it("asks the site again when the take itself failed", async () => {
		vi.mocked(call).mockRejectedValueOnce(new Error("offline"));
		const promptStart = new PromptStart();
		const start = vi.fn().mockResolvedValue(undefined);
		expect(await promptStart.begin(READY, start)).toMatchObject({ kind: "failed" });
		expect(start).not.toHaveBeenCalled();
		expect(await promptStart.startWith(DESCRIPTION, start)).toEqual({ kind: "started" });
	});
});

describe("starting another way", () => {
	it("has the site forget it, so no later open runs it", async () => {
		await new PromptStart().discard();
		expect(call).toHaveBeenCalledWith("frappe_page.tenant.start.take");
		expect(frappePage.fp.start).toBeUndefined();
		expect(await new PromptStart().begin(READY, vi.fn())).toEqual({ kind: "elsewhere" });
	});

	it("still lets the user come back and start from it on the same screen, without asking the site again", async () => {
		const promptStart = new PromptStart();
		await promptStart.discard();
		const start = vi.fn().mockResolvedValue(undefined);
		expect(await promptStart.startWith(DESCRIPTION, start)).toEqual({ kind: "started" });
		expect(call).toHaveBeenCalledTimes(1);
	});

	it("never throws when the site can't be reached", async () => {
		vi.mocked(call).mockRejectedValue(new Error("offline"));
		await expect(new PromptStart().discard()).resolves.toBeUndefined();
	});
});
