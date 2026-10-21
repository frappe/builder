import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChannelCallError } from "frappe-builder-extension-sdk/transport";
import call from "../../../../frappe-ui/src/utils/call";
import { useList } from "../../../../frappe-ui/src/data-fetching/useList/useList";
import { createDocumentResource } from "../../../../frappe-ui/src/resources/documentResource";
import { setConfig } from "../../../../frappe-ui/src/utils/config";
import { frappeRequest } from "../../../../frappe-ui/src/utils/frappeRequest";
import { installFetchBridge } from "../../../extension-sdk/src/runtime/fetchBridge";

/**
 * The SDK's fetch bridge, read by frappe-ui itself.
 *
 * `fetchBridge.test.ts` checks the envelopes the bridge writes. This file checks
 * that frappe-ui reads them as Frappe's own, so a change on either side that
 * breaks an extension's data layer fails here. It lives on the host side because
 * the SDK folder is copied to a repo that has no frappe-ui checkout.
 *
 * frappe-ui is imported by source path: its package index pulls in `.vue` files,
 * which this test config does not compile.
 */
let answer: unknown = null;
let thrown: unknown = null;

vi.mock("../../../extension-sdk/src/runtime/connect", () => ({
	HOST_ORIGIN: "http://builder.test",
	getChannel: () => ({
		call: () => (thrown ? Promise.reject(thrown) : Promise.resolve(answer)),
	}),
}));

vi.stubGlobal("location", {
	href: "http://builder.test/builder_extension",
	hostname: "builder.test",
	origin: "http://builder.test",
});
// frappeRequest reads `window.location` for its site header
vi.stubGlobal("window", globalThis);

// both sides read `fetch` and `location` at request time, so installing after the imports is enough
installFetchBridge();

// what an extension's entry does, as any Frappe app's does: resources default to a
// plain fetcher that adds no /api/method prefix
setConfig("resourceFetcher", frappeRequest);

beforeEach(() => {
	answer = null;
	thrown = null;
});

describe("call()", () => {
	it("resolves with the answer", async () => {
		answer = { data: [{ name: "CON-1" }] };

		expect(await call("frappe.client.get_list", { doctype: "Contact" })).toEqual([{ name: "CON-1" }]);
	});

	it("rejects with an exc_type an onError can branch on", async () => {
		thrown = new ChannelCallError({ message: "Not allowed.", code: "permission_required" });

		const error = await call("frappe.client.get_list", {}).catch((caught: unknown) => caught);

		expect(error).toMatchObject({ exc_type: "PermissionError", status: 403 });
		expect((error as { messages: string[] }).messages).toContain("Not allowed.");
	});
});

describe("useList()", () => {
	it("reads the rows and the page flag", async () => {
		answer = { data: [{ name: "A" }], hasNextPage: true };

		const list = useList({ doctype: "Contact", fields: ["name"], immediate: false });
		await list.fetch();

		expect(list.data).toEqual([{ name: "A" }]);
		expect(list.hasNextPage).toBe(true);
	});
});

describe("createDocumentResource()", () => {
	it("reads a doc method's result, and refreshes the document from the answer", async () => {
		answer = { data: 3, docs: [{ doctype: "Form", name: "F-1", title: "After" }] };

		const form = createDocumentResource({
			doctype: "Form",
			name: "F-1",
			auto: false,
			whitelistedMethods: { count: "count_responses" },
		});
		const result = await form.count.submit();

		expect(result).toBe(3);
		expect(form.doc).toMatchObject({ title: "After" });
	});
});
