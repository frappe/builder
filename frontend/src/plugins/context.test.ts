import { beforeEach, describe, expect, it, vi } from "vitest";

const { call } = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("frappe-ui", () => ({ call }));

import { createPluginContext, openHandlers } from "./context";

const plugin = (isDevelopment = false) => ({
	name: "acme/seo",
	label: "SEO",
	version: "1.0.0",
	entryUrl: "/main.js",
	isDevelopment,
});

const storage = new Map<string, string>();

describe("the context of a plugin", () => {
	beforeEach(() => {
		storage.clear();
		call.mockReset();
		openHandlers.clear();
		vi.stubGlobal("localStorage", {
			getItem: (key: string) => storage.get(key) ?? null,
			setItem: (key: string, value: string) => storage.set(key, value),
		});
	});

	it("stores an installed plugin's state on the server, under its own name", async () => {
		await createPluginContext(plugin()).state.set({ theme: "dark" });

		expect(call).toHaveBeenCalledWith("builder.plugins.state.set_state", {
			plugin: "acme/seo",
			state: { theme: "dark" },
		});
	});

	it("stores a dev plugin's state in the browser, merged at the top level", async () => {
		const { state } = createPluginContext(plugin(true));

		await state.set({ theme: "dark" });
		await state.set({ page: 2 });
		await state.unset("theme");

		expect(await state.get()).toEqual({ page: 2 });
		expect(call).not.toHaveBeenCalled();
	});

	it("names what the Open button runs", () => {
		const open = () => {};

		createPluginContext(plugin()).setOpenHandler(open);

		expect(openHandlers.get("acme/seo")).toBe(open);
	});
});
