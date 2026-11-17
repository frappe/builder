import { createResource } from "frappe-ui";
import { beforeEach, describe, expect, it, vi } from "vitest";

const builderStore = vi.hoisted(() => ({ activeFolder: "" }));
const insert = vi.hoisted(() => vi.fn());
const getCount = vi.hoisted(() => vi.fn());

vi.mock("frappe-ui", () => ({
	createListResource: vi.fn(() => ({})),
	createResource: vi.fn(() => ({ submit: getCount })),
	dialog: {},
}));
vi.mock("@/data/webPage", () => ({ webPages: { insert: { submit: insert } } }));
vi.mock("@/data/builderProjectFolder", () => ({ default: {} }));
vi.mock("@/router", () => ({ default: { push: vi.fn() } }));
vi.mock("@/stores/builderStore", () => ({ default: () => builderStore }));
vi.mock("@/stores/pageStore", () => ({ default: () => ({}) }));
vi.mock("@/translation", () => ({ __: (text: string) => text }));
vi.mock("@/utils/helpers", () => ({ getRootBlockTemplate: () => ({ blockId: "root" }) }));

import { insertBlankPage } from "./pageActions";

/** The site's folders: get_count of one name answers 1 when it is among them. */
function folders(...names: string[]) {
	getCount.mockImplementation(async ({ filters }: { filters: { name: string } }) =>
		Number(names.includes(filters.name)),
	);
}

const savedFolder = () => insert.mock.calls[0][0].project_folder;

beforeEach(() => {
	builderStore.activeFolder = "";
	insert.mockReset().mockImplementation(async (page) => ({ name: "page-1", ...page }));
	getCount.mockReset();
	vi.mocked(createResource).mockClear();
});

describe("a new blank page", () => {
	it("goes into the selected folder while it exists", async () => {
		folders("Fronds");
		builderStore.activeFolder = "Fronds";

		await insertBlankPage();

		expect(savedFolder()).toBe("Fronds");
		expect(builderStore.activeFolder).toBe("Fronds");
		expect(createResource).toHaveBeenCalledWith({ url: "frappe.client.get_count" });
		expect(getCount).toHaveBeenCalledWith({ doctype: "Builder Project Folder", filters: { name: "Fronds" } });
	});

	it("goes into no folder when the remembered one is gone, and forgets it", async () => {
		folders("Ferns");
		builderStore.activeFolder = "Fronds 2";

		const page = await insertBlankPage();

		expect(page.name).toBe("page-1");
		expect(savedFolder()).toBeUndefined();
		expect(builderStore.activeFolder).toBe("");
	});

	it("leaves the selection alone when a folder asked for explicitly is gone", async () => {
		folders("Ferns");
		builderStore.activeFolder = "Ferns";

		await insertBlankPage("Deleted");

		expect(savedFolder()).toBeUndefined();
		expect(builderStore.activeFolder).toBe("Ferns");
	});

	it("asks nothing about folders when none is selected", async () => {
		await insertBlankPage();

		expect(savedFolder()).toBeUndefined();
		expect(getCount).not.toHaveBeenCalled();
	});

	it("fails as the save failed, for the caller to show", async () => {
		folders();
		insert.mockRejectedValue(Object.assign(new Error("insert"), { messages: ["Not permitted"] }));

		await expect(insertBlankPage()).rejects.toMatchObject({ messages: ["Not permitted"] });
	});
});
