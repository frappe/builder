import { beforeEach, describe, expect, it, vi } from "vitest";
import { page } from "../../../../extension-sdk/src/runtime/methods/editor";
import { pageMethods } from "../pageMethods";

const { pageStore, canvasStore } = vi.hoisted(() => ({
	pageStore: {
		activePage: null as { name: string; page_data_script: string } | null,
		loadPageData: vi.fn(),
		refreshActivePage: vi.fn(),
	},
	canvasStore: { activeCanvas: { setRootBlock: vi.fn() } },
}));

vi.mock("@/router", () => ({ default: {} }));
vi.mock("@/stores/pageStore", () => ({ default: () => pageStore }));
vi.mock("@/stores/canvasStore", () => ({ default: () => canvasStore }));
vi.mock("@/utils/helpers", () => ({ getBlockObject: vi.fn() }));
vi.mock("../../../../extension-sdk/src/runtime/methods/call", () => ({
	call: (method: string, params: unknown) => pageMethods[method].run(params, extension),
}));

const extension = { name: "acme/cms", label: "CMS", entryUrl: "/main.js", permissions: [] };

describe("page.refreshData", () => {
	beforeEach(() => {
		vi.resetAllMocks();
		pageStore.activePage = { name: "posts", page_data_script: "data.posts = frappe.get_all('CMS Post')" };
	});

	it("refreshes the open page data without reloading its record or canvas", async () => {
		await page.refreshData();

		expect(pageStore.loadPageData).toHaveBeenCalledExactlyOnceWith(pageStore.activePage);
		expect(pageStore.refreshActivePage).not.toHaveBeenCalled();
		expect(canvasStore.activeCanvas.setRootBlock).not.toHaveBeenCalled();
		expect(pageMethods["page.refreshData"].needs).toBeNull();
	});

	it("waits until the page data has refreshed", async () => {
		let finish = () => {};
		pageStore.loadPageData.mockImplementationOnce(() => new Promise<void>((resolve) => (finish = resolve)));
		let completed = false;
		const refreshing = page.refreshData().then(() => (completed = true));
		await Promise.resolve();
		expect(completed).toBe(false);

		finish();
		await refreshing;
		expect(completed).toBe(true);
	});

	it("rejects when the page data does not load", async () => {
		pageStore.loadPageData.mockRejectedValueOnce(new Error("The data script failed"));
		await expect(page.refreshData()).rejects.toThrow("The data script failed");
	});

	it("refuses the call when no page is open", async () => {
		pageStore.activePage = null;

		await expect(page.refreshData()).rejects.toMatchObject({ code: "no_canvas" });
		expect(pageStore.loadPageData).not.toHaveBeenCalled();
	});
});
