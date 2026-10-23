import { describe, expect, it, vi } from "vitest";

vi.mock("frappe-ui", () => ({
	call: vi.fn(async () => "https://hub.example.com"),
	createResource: vi.fn(() => ({ data: null, fetch: vi.fn() })),
}));
vi.mock("@/extensions/devExtension", () => ({ devExtension: { value: null }, isDevExtension: () => false }));
vi.mock("@/extensions/loader", () => ({ loadExtension: vi.fn(), runningExtensions: new Set() }));

import { getHubExtension } from "./extensions";

describe("Hub requests", () => {
	it("send no cookies and no CSRF token to the Hub", async () => {
		const message = { extension: { name: "acme/seo", label: "SEO" }, releases: [] };
		const fetch = vi.fn(async () => new Response(JSON.stringify({ message })));
		vi.stubGlobal("fetch", fetch);

		await getHubExtension("acme/seo");

		expect(fetch).toHaveBeenCalledWith(
			"https://hub.example.com/api/method/builder_hub.extensions.api.get_extension?name=acme%2Fseo&protocol_version=1",
			{ credentials: "omit" },
		);
	});
});
