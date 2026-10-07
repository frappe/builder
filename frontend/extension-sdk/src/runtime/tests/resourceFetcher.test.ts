import { createDocumentResource, createListResource, setConfig } from "frappe-ui";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { data } from "../methods";
import { resourceFetcher } from "../resourceFetcher";

// these tests drive the real frappe-ui resources, so a frappe-ui release that
// changes a URL or a param shape fails here
vi.mock("../methods", () => ({
	data: {
		getList: vi.fn(async () => [{ name: "TOKEN-1" }]),
		getCount: vi.fn(async () => 1),
		getDoc: vi.fn(async () => ({ name: "TOKEN-1", value: "#fff" })),
		insert: vi.fn(async () => ({ name: "TOKEN-2" })),
		update: vi.fn(async () => ({ name: "TOKEN-1" })),
		delete: vi.fn(async () => null),
	},
}));

const listOf = () =>
	createListResource({ doctype: "Builder Token", fields: ["name", "value"], pageLength: 5 });

beforeAll(() => setConfig("resourceFetcher", resourceFetcher));
beforeEach(() => vi.clearAllMocks());

describe("resourceFetcher with createListResource", () => {
	it("sends a list fetch to data.getList", async () => {
		await listOf().list.fetch();

		expect(data.getList).toHaveBeenCalledWith(
			"Builder Token",
			expect.objectContaining({ fields: ["name", "value"], start: 0, pageLength: 5 }),
		);
	});

	it("sends fetchOne with no fields as a list of every field", async () => {
		await createListResource({ doctype: "Builder Token" }).fetchOne.submit("TOKEN-1");

		expect(data.getList).toHaveBeenCalledWith(
			"Builder Token",
			expect.objectContaining({ fields: ["*"], filters: { name: "TOKEN-1" } }),
		);
	});

	it("sends insert, setValue and delete to the document methods", async () => {
		const list = listOf();
		await list.insert.submit({ token_name: "brand", type: "Color", value: "#000" });
		await list.setValue.submit({ name: "TOKEN-1", value: "#111" });
		await list.delete.submit("TOKEN-1");

		expect(data.insert).toHaveBeenCalledWith("Builder Token", expect.objectContaining({ value: "#000" }));
		expect(data.update).toHaveBeenCalledWith("Builder Token", "TOKEN-1", { value: "#111" });
		expect(data.delete).toHaveBeenCalledWith("Builder Token", "TOKEN-1");
	});

	it("refuses a URL with no route", async () => {
		const list = listOf();
		await list.runDocMethod.submit({ method: "validate", name: "TOKEN-1" }).catch(() => {});

		expect(list.runDocMethod.error?.message).toContain('no route for "run_doc_method"');
	});
});

describe("resourceFetcher with createDocumentResource", () => {
	it("reads and changes one document", async () => {
		const token = createDocumentResource({ doctype: "Builder Token", name: "TOKEN-1" });
		await token.reload();
		await token.setValue.submit({ value: "#222" });

		expect(data.getDoc).toHaveBeenCalledWith("Builder Token", "TOKEN-1");
		expect(data.update).toHaveBeenCalledWith("Builder Token", "TOKEN-1", { value: "#222" });
	});
});
