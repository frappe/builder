import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChannelCallError } from "../../shared/transport/createPortChannel";

/**
 * The channel and the network are mocked. Under test is the adapter's whole
 * contract: which requests go over the port, what they carry, and how the
 * answer is shaped so frappe-ui reads it as Frappe's own.
 */
const HOST = "http://builder.test";

const calls: Array<{ method: string; params: unknown }> = [];
let answer: unknown = { data: null };
let thrown: unknown = null;

vi.mock("../connect", () => ({
	HOST_ORIGIN: "http://builder.test",
	getChannel: () => ({
		call: (method: string, params: unknown) => {
			calls.push({ method, params });
			return thrown ? Promise.reject(thrown) : Promise.resolve(answer);
		},
	}),
}));

import { installFetchBridge } from "../fetchBridge";

const network = vi.fn(async () => new Response("from the network"));
const realFetch = globalThis.fetch;

beforeEach(() => {
	calls.length = 0;
	answer = { data: null };
	thrown = null;
	network.mockClear();
	vi.stubGlobal("location", { href: `${HOST}/builder_extension` });
	globalThis.fetch = network;
	installFetchBridge();
});

afterEach(() => {
	globalThis.fetch = realFetch;
	vi.unstubAllGlobals();
});

const refusal = (code: string) => new ChannelCallError({ message: "No.", code });

describe("what goes over the port", () => {
	it("sends a relative v1 call as it came", async () => {
		await fetch("/api/method/frappe.client.get_list", {
			method: "POST",
			body: JSON.stringify({ doctype: "Contact" }),
		});

		expect(network).not.toHaveBeenCalled();
		expect(calls).toEqual([
			{
				method: "data.request",
				params: { method: "POST", url: "/api/method/frappe.client.get_list", body: '{"doctype":"Contact"}' },
			},
		]);
	});

	it("keeps the query and sends no body for a GET", async () => {
		await fetch(`${HOST}/api/v2/document/Contact?limit=5`);

		expect(calls[0].params).toEqual({
			method: "GET",
			url: "/api/v2/document/Contact?limit=5",
			body: undefined,
		});
	});

	it("reads a Request object too", async () => {
		await fetch(new Request(`${HOST}/api/v2/document/Contact/CON-1`, { method: "DELETE" }));

		expect(calls[0].params).toMatchObject({ method: "DELETE", url: "/api/v2/document/Contact/CON-1" });
	});
});

describe("what goes to the network", () => {
	it.each([`${HOST}/assets/builder/logo.svg`, "https://api.example.com/api/method/x", "/files/a.png"])(
		"%s",
		async (url) => {
			const response = await fetch(url);

			expect(await response.text()).toBe("from the network");
			expect(calls).toEqual([]);
		},
	);
});

describe("the answer", () => {
	it("is v1's envelope for /api/method", async () => {
		answer = { data: [{ name: "CON-1" }] };

		const response = await fetch("/api/method/frappe.client.get_list");

		expect(response.status).toBe(200);
		expect(await response.json()).toEqual({ message: [{ name: "CON-1" }] });
	});

	it("is v2's envelope for /api/v2, with the page flag", async () => {
		answer = { data: [{ name: "CON-1" }], hasNextPage: true };

		const response = await fetch("/api/v2/document/Contact");

		expect(await response.json()).toEqual({ data: [{ name: "CON-1" }], has_next_page: true });
	});
});

describe("a doc method's answer", () => {
	it("carries the document beside the message in v1, which frappe-ui reads whole", async () => {
		answer = { data: 3, docs: [{ name: "F-1" }] };

		const response = await fetch("/api/method/run_doc_method");

		expect(await response.json()).toEqual({ message: 3, docs: [{ name: "F-1" }] });
	});

	it("carries it beside the data in v2", async () => {
		answer = { data: 3, docs: [{ name: "F-1" }] };

		const response = await fetch("/api/v2/document/Form/F-1/method/count");

		expect(await response.json()).toEqual({ data: 3, docs: [{ name: "F-1" }] });
	});
});

describe("a refusal", () => {
	it("says PermissionError in v1's shape when a permission is missing", async () => {
		thrown = refusal("permission_required");

		const response = await fetch("/api/method/frappe.client.get_list");

		expect(response.status).toBe(403);
		expect(await response.json()).toEqual({ exc_type: "PermissionError", message: "No." });
	});

	it("says it in v2's shape too", async () => {
		thrown = refusal("permission_required");

		const response = await fetch("/api/v2/document/Contact");

		expect(response.status).toBe(403);
		expect((await response.json()).errors[0]).toMatchObject({ type: "PermissionError", message: "No." });
	});

	it.each([
		["unsupported_request", 404, "DoesNotExistError"],
		["permission_required", 403, "PermissionError"],
		["rate_limited", 429, "RateLimitExceededError"],
		["server_error", 417, "ValidationError"],
	])("maps %s to %i %s", async (code, status, type) => {
		thrown = refusal(code);

		const response = await fetch("/api/method/myapp.api.x");

		expect(response.status).toBe(status);
		expect((await response.json()).exc_type).toBe(type);
	});
});
