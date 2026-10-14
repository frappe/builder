import { beforeEach, describe, expect, it, vi } from "vitest";
import { pageMethods } from "../pageMethods";

const { pageStore, push } = vi.hoisted(() => ({
	pageStore: {
		selectedPage: "first",
		activePage: { name: "first" },
		settingPage: false,
		waitTillPageIsSaved: vi.fn(),
	},
	push: vi.fn(),
}));
vi.mock("@/router", () => ({ default: { push } }));
vi.mock("@/stores/pageStore", () => ({ default: () => pageStore }));
vi.mock("@/stores/canvasStore", () => ({ default: vi.fn() }));
vi.mock("@/utils/helpers", () => ({ getBlockObject: vi.fn() }));

const extension = { name: "acme/cms", entryUrl: "/main.js", permissions: [] };

describe("page.open", () => {
	beforeEach(() => {
		vi.resetAllMocks();
		Object.assign(pageStore, { selectedPage: "first", activePage: { name: "first" }, settingPage: false });
		push.mockImplementation(async ({ params }) => {
			pageStore.selectedPage = params.pageId;
			pageStore.activePage = { name: params.pageId };
		});
	});

	it("finishes saving the current page before navigating", async () => {
		await pageMethods["page.open"].run({ name: "next" }, extension);
		expect(pageStore.waitTillPageIsSaved).toHaveBeenCalledOnce();
		expect(pageStore.waitTillPageIsSaved.mock.invocationCallOrder[0]).toBeLessThan(
			push.mock.invocationCallOrder[0],
		);
	});

	it("does not navigate if saving fails", async () => {
		pageStore.waitTillPageIsSaved.mockRejectedValue(new Error("Save failed"));
		await expect(pageMethods["page.open"].run({ name: "next" }, extension)).rejects.toThrow("Save failed");
		expect(push).not.toHaveBeenCalled();
	});

	it("keeps the current page without a redundant save", async () => {
		await pageMethods["page.open"].run({ name: "first" }, extension);
		expect(pageStore.waitTillPageIsSaved).not.toHaveBeenCalled();
		expect(push).not.toHaveBeenCalled();
	});
});
