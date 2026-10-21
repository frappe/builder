import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * The Frappe call is mocked. Under test is the route table: which server method
 * each frappe-ui request reaches, with which names, and what a request with no
 * route does.
 */
type Call = { url: string; params: Record<string, unknown> };

const submitted: Call[] = [];
let answer: unknown = [];

vi.mock("frappe-ui", () => ({
	createResource: ({ url }: { url: string }) => ({
		submit: (params: Record<string, unknown>) => {
			submitted.push({ url, params });
			return Promise.resolve(answer);
		},
	}),
}));

// a write also reloads the editor's copy and tells the other frames. Neither is under test here
vi.mock("../editorRefresh", () => ({ refreshEditor: () => Promise.resolve() }));
vi.mock("../../bridge/bridge", () => ({ bridge: { getChannels: () => [] } }));

import { requestMethods } from "../requestMethods";
import type { InstalledExtension, Permission } from "frappe-builder-extension-sdk/types";

const record = (permissions: Permission[] = ["data.access", "method.call"]): InstalledExtension => ({
	name: "acme/crm",
	label: "CRM",
	entryUrl: "/main.js",
	permissions,
});

const send = (method: string, url: string, body?: unknown, extension = record()) =>
	requestMethods["data.request"].run(
		{ method, url, body: body === undefined ? undefined : JSON.stringify(body) },
		extension,
	) as Promise<{ data: unknown; hasNextPage?: boolean; docs?: unknown[] }>;

const last = () => submitted[submitted.length - 1];

const codeOf = async (run: () => unknown) => {
	try {
		await run();
	} catch (error) {
		return (error as { code?: string }).code;
	}
	return undefined;
};

beforeEach(() => {
	submitted.length = 0;
	answer = [];
});

describe("the permission", () => {
	it("is named by each route, not by the method", () => {
		expect(requestMethods["data.request"].needs).toBeNull();
	});

	it("needs data.access for a document request", async () => {
		const call = () => send("GET", "/api/v2/document/Contact", undefined, record(["method.call"]));

		expect(await codeOf(call)).toBe("permission_required");
		expect(submitted).toEqual([]);
	});

	it("needs method.call for a method, whatever else the extension holds", async () => {
		const call = () => send("POST", "/api/method/myapp.api.export", {}, record(["data.access"]));

		expect(await codeOf(call)).toBe("permission_required");
		expect(submitted).toEqual([]);
	});
});

describe("a request with no route", () => {
	it.each([
		["GET", "/api/v2/document/Contact/CON-1/copy"],
		["POST", "/api/v2/document/Contact/bulk_delete"],
		["GET", "/api/v2/doctype/Contact/discovery"],
		["POST", "/api/v2/doctype/Contact/count"],
		["GET", "/api/v2/method/a/b/c"],
		["GET", "/api/method"],
		["GET", "/files/report.pdf"],
	])("refuses %s %s, never forwards it", async (method, url) => {
		expect(await codeOf(() => send(method, url))).toBe("unsupported_request");
		expect(submitted).toEqual([]);
	});

	it("refuses a body that is not a JSON object", async () => {
		expect(await codeOf(() => send("POST", "/api/method/frappe.client.get_list", ["Contact"]))).toBe(
			"invalid_params",
		);
	});
});

describe("v1, frappe.client", () => {
	it("routes get_list and translates Frappe's names", async () => {
		await send("POST", "/api/method/frappe.client.get_list", {
			doctype: "Contact",
			fields: ["name"],
			filters: { status: "Open" },
			or_filters: [["city", "=", "Pune"]],
			order_by: "modified desc",
			group_by: "status",
			limit_start: 20,
			limit_page_length: 10,
		});

		expect(last()).toEqual({
			url: "builder.extensions.data.get_list",
			params: {
				extension: "acme/crm",
				doctype: "Contact",
				fields: ["name"],
				filters: { status: "Open" },
				or_filters: [["city", "=", "Pune"]],
				order_by: "modified desc",
				group_by: "status",
				limit_start: 20,
				limit_page_length: 10,
			},
		});
	});

	it("reads JSON and numbers out of a query string", async () => {
		await send(
			"GET",
			'/api/method/frappe.client.get_list?doctype=Contact&fields=["name"]&limit_page_length=5&order_by=',
		);

		expect(last().params).toMatchObject({ fields: ["name"], limit_page_length: 5 });
		expect(last().params.order_by).toBeUndefined();
	});

	it("answers with what the server sent, for the frame to wrap", async () => {
		answer = [{ name: "CON-1" }];

		expect(await send("POST", "/api/method/frappe.client.get_list", { doctype: "Contact" })).toEqual({
			data: [{ name: "CON-1" }],
		});
	});

	it("refuses a child table, whose permission belongs to its parent", async () => {
		const body = { doctype: "Contact Email", parent: "Contact" };
		expect(await codeOf(() => send("POST", "/api/method/frappe.client.get_list", body))).toBe(
			"unsupported_request",
		);
	});

	it("routes get, get_count and delete", async () => {
		await send("POST", "/api/method/frappe.client.get", { doctype: "Contact", name: "CON-1" });
		expect(last().url).toBe("builder.extensions.data.get_doc");

		await send("POST", "/api/method/frappe.client.get_count", { doctype: "Contact", filters: {} });
		expect(last().url).toBe("builder.extensions.data.get_count");

		await send("POST", "/api/method/frappe.client.delete", { doctype: "Contact", name: "CON-1" });
		expect(last()).toMatchObject({ url: "builder.extensions.data.delete_doc", params: { name: "CON-1" } });
	});

	it("lifts insert's doctype out of the document", async () => {
		await send("POST", "/api/method/frappe.client.insert", {
			doc: { doctype: "Contact", first_name: "Ada" },
		});

		expect(last()).toMatchObject({
			url: "builder.extensions.data.insert_doc",
			params: { doctype: "Contact", doc: { doctype: "Contact", first_name: "Ada" } },
		});
	});

	it("reads set_value's patch in both of its forms", async () => {
		const target = { doctype: "Contact", name: "CON-1" };

		await send("POST", "/api/method/frappe.client.set_value", { ...target, fieldname: { status: "Open" } });
		expect(last().params.doc).toEqual({ status: "Open" });

		await send("POST", "/api/method/frappe.client.set_value", {
			...target,
			fieldname: "status",
			value: "Open",
		});
		expect(last().params.doc).toEqual({ status: "Open" });
	});
});

describe("v2, documents", () => {
	it("asks for one row more than the page and answers whether there is a next page", async () => {
		answer = [{ name: "A" }, { name: "B" }, { name: "C" }];

		const page = await send("GET", '/api/v2/document/Contact?fields=["name"]&start=4&limit=2');

		expect(last().params).toMatchObject({ doctype: "Contact", limit_start: 4, limit_page_length: 3 });
		expect(page).toEqual({ data: [{ name: "A" }, { name: "B" }], hasNextPage: true });
	});

	it("answers the last page with no next page", async () => {
		answer = [{ name: "A" }];

		expect(await send("GET", "/api/v2/document/Contact?limit=2")).toEqual({
			data: [{ name: "A" }],
			hasNextPage: false,
		});
	});

	it("uses Frappe's page size when the list names none", async () => {
		await send("GET", "/api/v2/document/Contact");

		expect(last().params.limit_page_length).toBe(21);
	});

	it("refuses a limit that is not a number", async () => {
		expect(await codeOf(() => send("GET", "/api/v2/document/Contact?limit=all"))).toBe("invalid_params");
	});

	it("inserts the body as the document", async () => {
		await send("POST", "/api/v2/document/Contact", { first_name: "Ada" });

		expect(last()).toMatchObject({
			url: "builder.extensions.data.insert_doc",
			params: { doctype: "Contact", doc: { first_name: "Ada" } },
		});
	});

	it("reads, updates and deletes one document", async () => {
		await send("GET", "/api/v2/document/Contact/CON-1");
		expect(last()).toMatchObject({ url: "builder.extensions.data.get_doc", params: { name: "CON-1" } });

		await send("PATCH", "/api/v2/document/Contact/CON-1", { first_name: "Ada" });
		expect(last()).toMatchObject({
			url: "builder.extensions.data.update_doc",
			params: { doc: { first_name: "Ada" } },
		});

		await send("PUT", "/api/v2/document/Contact/CON-1", { first_name: "Grace" });
		expect(last().url).toBe("builder.extensions.data.update_doc");

		expect(await send("DELETE", "/api/v2/document/Contact/CON-1")).toEqual({ data: "ok" });
		expect(last().url).toBe("builder.extensions.data.delete_doc");
	});

	it("keeps the empty values in a body, so a patch can clear a field", async () => {
		await send("PATCH", "/api/v2/document/Contact/CON-1", { first_name: "", company: null });

		expect(last().params.doc).toEqual({ first_name: "", company: null });
	});

	it("keeps an encoded slash inside one name", async () => {
		await send("GET", "/api/v2/document/Web%20Page/about%2Fteam");

		expect(last().params).toMatchObject({ doctype: "Web Page", name: "about/team" });
	});

	it("routes count and meta", async () => {
		await send("GET", '/api/v2/doctype/Contact/count?filters={"status":"Open"}');
		expect(last()).toMatchObject({
			url: "builder.extensions.data.get_count",
			params: { filters: { status: "Open" } },
		});

		await send("GET", "/api/v2/doctype/Contact/meta");
		expect(last()).toEqual({
			url: "builder.extensions.data.get_meta",
			params: { extension: "acme/crm", doctype: "Contact" },
		});
	});
});

describe("methods", () => {
	it("sends a v1 module method with its verb and arguments", async () => {
		answer = "exported";

		const sent = await send("POST", "/api/method/myapp.api.export", { format: "csv" });

		expect(last()).toEqual({
			url: "builder.extensions.methods.run_method",
			params: { extension: "acme/crm", method: "myapp.api.export", verb: "POST", args: { format: "csv" } },
		});
		expect(sent).toEqual({ data: "exported" });
	});

	it("leaves the floor to the server, which owns it", async () => {
		await send("GET", "/api/method/frappe.desk.search.search_link?txt=a");

		expect(last().params).toMatchObject({ method: "frappe.desk.search.search_link", verb: "GET" });
	});

	it("names a v2 method by its dotted path, and a doctype method as <DocType>.<method>", async () => {
		await send("POST", "/api/v2/method/myapp.api.export");
		expect(last().params.method).toBe("myapp.api.export");

		await send("GET", "/api/v2/method/Form/get_summary");
		expect(last().params.method).toBe("Form.get_summary");
	});

	it("runs a v1 doc method and answers with the document beside the result", async () => {
		answer = { message: 3, docs: [{ name: "F-1" }] };

		const sent = await send("POST", "/api/method/run_doc_method", {
			dt: "Form",
			dn: "F-1",
			method: "count_responses",
			args: '{"since":"2026-01-01"}',
		});

		expect(last()).toEqual({
			url: "builder.extensions.methods.run_doc_method",
			params: {
				extension: "acme/crm",
				doctype: "Form",
				name: "F-1",
				method: "count_responses",
				verb: "POST",
				args: { since: "2026-01-01" },
			},
		});
		expect(sent).toEqual({ data: 3, docs: [{ name: "F-1" }] });
	});

	it("reads a v2 doc method from the end of the path, so a name may hold a slash", async () => {
		answer = { message: null, docs: [] };

		await send("GET", "/api/v2/document/Web%20Page/about%2Fteam/method/get_summary");

		expect(last().params).toMatchObject({
			doctype: "Web Page",
			name: "about/team",
			method: "get_summary",
			verb: "GET",
		});
	});
});
