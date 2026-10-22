import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("frappe-ui", () => ({ call: vi.fn().mockResolvedValue(undefined) }));
vi.mock("./loader", () => ({ loadExtension: vi.fn(), runningExtensions: new Set<string>() }));

import { call } from "frappe-ui";
import { devExtension, loadDevExtension } from "./devExtension";
import { loadExtension, runningExtensions } from "./loader";

const DEV_SERVER = "http://localhost:5173";

const memoryStorage = () => {
	const items = new Map<string, string>();
	return {
		getItem: (key: string) => items.get(key) ?? null,
		setItem: (key: string, value: string) => void items.set(key, value),
		removeItem: (key: string) => void items.delete(key),
	};
};

const descriptor = { name: "acme/seo", label: "SEO", version: "0.0.0", entry: "/src/main.ts" };

describe("dev extension", () => {
	beforeEach(() => {
		vi.stubGlobal("localStorage", memoryStorage());
		vi.stubGlobal("sessionStorage", memoryStorage());
		vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => descriptor }));
		vi.mocked(call).mockClear();
		vi.mocked(loadExtension).mockClear();
		runningExtensions.clear();
		devExtension.value = null;
	});

	it("loads into the running editor", async () => {
		const extension = await loadDevExtension(`${DEV_SERVER}/`);

		expect(extension.entryUrl).toBe(`${DEV_SERVER}/src/main.ts`);
		expect(loadExtension).toHaveBeenCalledOnce();
	});

	it("refuses an extension that the editor already runs, so two copies never run", async () => {
		runningExtensions.add("acme/seo");

		await expect(loadDevExtension(DEV_SERVER)).rejects.toThrow("already runs here");
		expect(call).not.toHaveBeenCalled();
		expect(loadExtension).not.toHaveBeenCalled();
	});
});
