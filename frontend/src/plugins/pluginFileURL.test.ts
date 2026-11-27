import { describe, expect, it, vi } from "vitest";

vi.mock("frappe-ui", () => ({ call: vi.fn() }));
vi.mock("@/utils/frappePage", () => ({ fp: { mount: "/acme" }, isMounted: true, isIsolated: true }));

import { pluginFileURL } from "./loader";

describe("pluginFileURL under a frappe.page mount", () => {
	it("puts a site's own plugin file under the mount", () => {
		expect(pluginFileURL("/files/builder_plugins/a1/0123456789ab/main.js")).toBe(
			"/acme/files/builder_plugins/a1/0123456789ab/main.js"
		);
	});

	it("leaves an app's build and other origins alone", () => {
		expect(pluginFileURL("/assets/acme_app/builder_plugins/seo/main.js?v=1")).toBe(
			"/assets/acme_app/builder_plugins/seo/main.js?v=1"
		);
		expect(pluginFileURL("http://localhost:5173/src/main.ts")).toBe("http://localhost:5173/src/main.ts");
	});
});
