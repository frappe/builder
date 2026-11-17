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

/** The site's copy (frappe_page.tenant.start): take holds it for one tab, give_back frees it, done forgets it. */
const site = { text: null as string | null, held: false };

function siteKeeps(description: string | null, held = false) {
	Object.assign(site, { text: description, held });
	vi.mocked(call).mockImplementation(async (method: string) => {
		if (method === "frappe_page.tenant.start.take") {
			if (!site.text || site.held) return null;
			site.held = true;
			return site.text;
		}
		if (method === "frappe_page.tenant.start.give_back") return void (site.held = false);
		if (method === "frappe_page.tenant.start.done") return void (site.text = null);
		throw new Error(`unexpected call ${method}`);
	});
}

const calls = () => vi.mocked(call).mock.calls.map(([method]) => method.split(".").pop());

/** A start that opens the page and hands Bob the turn; `bob` says how the turn went. */
function opensPage() {
	const bob = { settled: undefined as undefined | ((accepted: boolean) => void) };
	const start = vi.fn(async (_description: string, settled: (accepted: boolean) => void) => {
		bob.settled = settled;
	});
	return { start, bob };
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
	it("holds it while a page opens and Bob gets the turn, and the site forgets it once he accepts", async () => {
		const { start, bob } = opensPage();
		expect(await new PromptStart().begin(READY, start)).toEqual({ kind: "started" });
		expect(start).toHaveBeenCalledWith(DESCRIPTION, expect.any(Function));
		// another tab, or a reload, finds none meanwhile
		expect(site).toEqual({ text: DESCRIPTION, held: true });
		expect(await new PromptStart().begin(READY, vi.fn())).toEqual({ kind: "elsewhere" });

		await bob.settled!(true);
		expect(site.text).toBeNull();
		expect(calls()).toEqual(["take", "take", "done"]);
	});

	it("runs once: after it is taken, a reload's boot names none and the home route stays", async () => {
		await new PromptStart().begin(READY, opensPage().start);
		expect(frappePage.fp.start).toBeUndefined();
		expect(promptStartRedirect()).toBeUndefined();
	});

	it("starts nothing when another tab holds it", async () => {
		siteKeeps(DESCRIPTION, true);
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

	it("gives it back when the page couldn't open, so a reload offers it again, and a retry takes it again", async () => {
		const promptStart = new PromptStart();
		const failing = vi.fn().mockRejectedValue(new Error("no permission"));
		expect(await promptStart.begin(READY, failing)).toMatchObject({ kind: "failed" });
		expect(site).toEqual({ text: DESCRIPTION, held: false });

		const { start, bob } = opensPage();
		expect(await promptStart.startWith("A bakery called Crumb, in Pune.", start)).toEqual({
			kind: "started",
		});
		expect(start).toHaveBeenCalledWith("A bakery called Crumb, in Pune.", expect.any(Function));
		await bob.settled!(true);
		expect(calls()).toEqual(["take", "give_back", "take", "done"]);
		expect(site.text).toBeNull();
	});

	it("gives it back when Bob never accepted the turn, since only the composer has it now", async () => {
		const { start, bob } = opensPage();
		expect(await new PromptStart().begin(READY, start)).toEqual({ kind: "started" });
		await bob.settled!(false);
		expect(site).toEqual({ text: DESCRIPTION, held: false });
	});

	it("settles once: a word after the first changes nothing", async () => {
		const { start, bob } = opensPage();
		await new PromptStart().begin(READY, start);
		await bob.settled!(false);
		await bob.settled!(true);
		expect(calls()).toEqual(["take", "give_back"]);
		expect(site.text).toBe(DESCRIPTION);
	});

	it("asks the site again when the take itself failed", async () => {
		vi.mocked(call).mockRejectedValueOnce(new Error("offline"));
		const promptStart = new PromptStart();
		const { start } = opensPage();
		expect(await promptStart.begin(READY, start)).toMatchObject({ kind: "failed" });
		expect(start).not.toHaveBeenCalled();
		expect(await promptStart.startWith(DESCRIPTION, start)).toEqual({ kind: "started" });
	});

	it("still starts when the site can't hear how it went: the site settles it itself", async () => {
		const { start, bob } = opensPage();
		await new PromptStart().begin(READY, start);
		vi.mocked(call).mockRejectedValue(new Error("offline"));
		await expect(bob.settled!(true)).resolves.toBeUndefined();
	});
});

describe("starting another way", () => {
	it("has the site forget it, so no later open runs it", async () => {
		await new PromptStart().discard();
		expect(calls()).toEqual(["done"]);
		expect(frappePage.fp.start).toBeUndefined();
		expect(await new PromptStart().begin(READY, vi.fn())).toEqual({ kind: "elsewhere" });
	});

	it("still lets the user come back and start from it on the same screen, without asking the site again", async () => {
		const promptStart = new PromptStart();
		await promptStart.discard();
		const { start, bob } = opensPage();
		expect(await promptStart.startWith(DESCRIPTION, start)).toEqual({ kind: "started" });
		// the site has nothing left to settle
		await bob.settled!(false);
		expect(calls()).toEqual(["done"]);
	});

	it("never throws when the site can't be reached", async () => {
		vi.mocked(call).mockRejectedValue(new Error("offline"));
		await expect(new PromptStart().discard()).resolves.toBeUndefined();
	});
});
