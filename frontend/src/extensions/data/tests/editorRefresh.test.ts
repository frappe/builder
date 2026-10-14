import { beforeEach, describe, expect, it, vi } from "vitest";
import { refreshEditor } from "../editorRefresh";

const { list, resources, pageStore, componentStore, blockTemplateStore } = vi.hoisted(() => ({
	list: () => ({ reload: vi.fn() }),
	resources: {} as Record<string, { reload: ReturnType<typeof vi.fn> }>,
	pageStore: {
		activePage: { name: "home", client_scripts: [{ builder_script: "linked-script" }] },
		refreshActivePage: vi.fn(),
	},
	componentStore: { refreshComponent: vi.fn() },
	blockTemplateStore: { blockTemplateMap: new Map([["hero", {}]]) },
}));

vi.mock("@/data/allWebPages", () => ({
	allWebPages: (resources.allWebPages = list()),
	linkablePages: (resources.linkablePages = list()),
}));
vi.mock("@/data/webPage", () => ({ webPages: (resources.webPages = list()) }));
vi.mock("@/data/builderToken", () => ({ default: (resources.tokens = list()) }));
vi.mock("@/data/userFonts", () => ({ default: (resources.fonts = list()) }));
vi.mock("@/data/builderBlockTemplate", () => ({ default: (resources.templates = list()) }));
vi.mock("@/data/builderSettings", () => ({ builderSettings: (resources.settings = list()) }));
vi.mock("@/stores/pageStore", () => ({ default: () => pageStore }));
vi.mock("@/stores/componentStore", () => ({ default: () => componentStore }));
vi.mock("@/stores/blockTemplateStore", () => ({ default: () => blockTemplateStore }));

describe("refreshEditor", () => {
	beforeEach(() => vi.clearAllMocks());

	it("reloads the open page after a write to it", async () => {
		await refreshEditor("Builder Page", "home", "update");

		expect(pageStore.refreshActivePage).toHaveBeenCalledOnce();
		expect(resources.webPages.reload).not.toHaveBeenCalled();
	});

	it("leaves the open page alone after a write to another page", async () => {
		await refreshEditor("Builder Page", "about", "update");

		expect(pageStore.refreshActivePage).not.toHaveBeenCalled();
	});

	it("reloads the page lists after a new page", async () => {
		await refreshEditor("Builder Page", "about", "insert");

		["webPages", "allWebPages", "linkablePages"].forEach((name) =>
			expect(resources[name].reload).toHaveBeenCalledOnce(),
		);
	});

	it("reloads the open page only for a script linked to it", async () => {
		await refreshEditor("Builder Client Script", "other-script", "update");
		expect(pageStore.refreshActivePage).not.toHaveBeenCalled();

		await refreshEditor("Builder Client Script", "linked-script", "update");
		expect(pageStore.refreshActivePage).toHaveBeenCalledOnce();
	});

	it("tells the component store when a component is deleted", async () => {
		await refreshEditor("Builder Component", "card", "delete");

		expect(componentStore.refreshComponent).toHaveBeenCalledWith("card", true);
	});

	it("drops a cached block template and reloads the list", async () => {
		await refreshEditor("Block Template", "hero", "update");

		expect(blockTemplateStore.blockTemplateMap.has("hero")).toBe(false);
		expect(resources.templates.reload).toHaveBeenCalledOnce();
	});

	it.each([
		["Builder Token", "tokens"],
		["User Font", "fonts"],
		["Builder Settings", "settings"],
	])("reloads the %s list", async (doctype, resource) => {
		await refreshEditor(doctype, "any", "update");

		expect(resources[resource].reload).toHaveBeenCalledOnce();
	});

	it("does nothing for a doctype the editor does not keep", async () => {
		await expect(refreshEditor("ToDo", "1", "update")).resolves.toBeUndefined();
	});

	// the write already succeeded, so the extension must still get its answer
	it("does not fail the call when a reload fails", async () => {
		const error = vi.spyOn(console, "error").mockImplementation(() => {});
		pageStore.refreshActivePage.mockRejectedValueOnce(new Error("offline"));

		await expect(refreshEditor("Builder Page", "home", "update")).resolves.toBeUndefined();
		expect(error).toHaveBeenCalledOnce();
	});
});
