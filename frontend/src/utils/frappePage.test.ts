import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// the tenant's own fetch: index.html wraps it to prefix the mount, so control calls must never use it
const tenantFetch = vi.fn();
const appFetch = vi.fn();

vi.hoisted(() => {
	vi.stubGlobal("window", {
		fp: { mount: "/acme", editor_base: "/acme", app_url: "https://frappe.page", site_subdomain: "acme" },
		csrf_token: "tenant-token",
		location: { pathname: "/acme/home", search: "" },
	});
});

import { controlCall, ControlError, fp, openSiteURL, setControlCSRFToken } from "./frappePage";

const ok = (message: unknown) => ({ ok: true, status: 200, json: async () => ({ message }) });

describe("controlCall", () => {
	beforeEach(() => {
		vi.stubGlobal("fetch", tenantFetch);
		fp.appFetch = appFetch;
		appFetch.mockReset();
		tenantFetch.mockReset();
	});

	it("sends a GET's arguments as the query string, through the unwrapped fetch", async () => {
		appFetch.mockResolvedValue(ok({ available: true }));

		const result = await controlCall("frappe_page.api.check_subdomain", { subdomain: "new-name" });

		expect(result).toEqual({ available: true });
		const [url, init] = appFetch.mock.calls[0];
		expect(url).toBe("/api/method/frappe_page.api.check_subdomain?subdomain=new-name");
		expect(init.method).toBeUndefined();
		expect(init.headers["X-Frappe-CSRF-Token"]).toBeUndefined();
		expect(tenantFetch).not.toHaveBeenCalled();
	});

	it("posts JSON with the control session's CSRF token, never the tenant's", async () => {
		appFetch.mockResolvedValue(ok({ email: "a@example.com" }));
		setControlCSRFToken("control-token");

		await controlCall("frappe_page.api.invite", { site: "s-1", email: "a@example.com" }, { post: true });

		const [url, init] = appFetch.mock.calls[0];
		expect(url).toBe("/api/method/frappe_page.api.invite");
		expect(init.method).toBe("POST");
		expect(init.headers["X-Frappe-CSRF-Token"]).toBe("control-token");
		expect(JSON.parse(init.body)).toEqual({ site: "s-1", email: "a@example.com" });
	});

	it("refuses a method name that is not a dotted path", async () => {
		await expect(controlCall("../../acme/api/method/x")).rejects.toBeInstanceOf(ControlError);
		expect(appFetch).not.toHaveBeenCalled();
	});

	it("reports the HTTP status and the exception type", async () => {
		appFetch.mockResolvedValue({
			ok: false,
			status: 400,
			json: async () => ({ exc_type: "CSRFTokenError" }),
		});

		const error = await controlCall("frappe_page.api.invite", {}, { post: true }).catch((e) => e);

		expect(error).toBeInstanceOf(ControlError);
		expect(error.status).toBe(400);
		expect(error.type).toBe("CSRFTokenError");
	});
});

describe("openSiteURL", () => {
	it("opens a site through the app host, then goes to the given editor path", () => {
		expect(openSiteURL("blog")).toBe("https://frappe.page/open/blog");
		expect(openSiteURL("new", "/new/home")).toBe("https://frappe.page/open/new?redirect-to=%2Fnew%2Fhome");
	});
});

describe("isIsolated", () => {
	const hostWindow = globalThis.window;
	const boot = async (fp: object) => {
		vi.resetModules();
		vi.stubGlobal("window", { fp });
		return import("./frappePage");
	};

	afterEach(() => {
		vi.stubGlobal("window", hostWindow);
	});

	it("isolates a mounted editor, which is no host editor", async () => {
		const { isHostEditor, isIsolated, isMounted } = await boot({ mount: "/acme" });

		expect([isMounted, isIsolated, isHostEditor]).toEqual([true, true, false]);
	});

	it("isolates the app host's own editor, which has no mount", async () => {
		const { isHostEditor, isIsolated, isMounted } = await boot({ isolate: 1 });

		expect([isMounted, isIsolated, isHostEditor]).toEqual([false, true, true]);
	});

	it("leaves an editor outside frappe.page as it was", async () => {
		const { isHostEditor, isIsolated, isMounted } = await boot({});

		expect([isMounted, isIsolated, isHostEditor]).toEqual([false, false, false]);
	});
});
