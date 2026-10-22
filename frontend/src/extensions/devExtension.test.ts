import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("frappe-ui", () => ({ call: vi.fn().mockResolvedValue(undefined) }));
vi.mock("./loader", () => ({ loadExtension: vi.fn(), runningExtensions: new Set<string>() }));

import { devExtension, getDevSessionExtension, loadDevExtension } from "./devExtension";
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
		vi.stubGlobal("window", { is_developer_mode: true });
		vi.stubGlobal("localStorage", memoryStorage());
		vi.stubGlobal("sessionStorage", memoryStorage());
		vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => descriptor }));
		vi.mocked(loadExtension).mockClear();
		runningExtensions.clear();
		devExtension.value = null;
	});

	it("loads into the running editor when no installed copy runs", async () => {
		const extension = await loadDevExtension(`${DEV_SERVER}/`);

		expect(extension?.entryUrl).toBe(`${DEV_SERVER}/src/main.ts`);
		expect(loadExtension).toHaveBeenCalledOnce();
		expect(getDevSessionExtension()).toBe("acme/seo");
	});

	it("waits for a reload when the installed copy runs, so two copies never run", async () => {
		runningExtensions.add("acme/seo");

		expect(await loadDevExtension(DEV_SERVER)).toBeNull();
		expect(loadExtension).not.toHaveBeenCalled();
		// the reload skips the installed copy and then restores the dev copy
		expect(getDevSessionExtension()).toBe("acme/seo");
	});

	it("skips no installed copy outside developer mode, where no dev copy is restored", async () => {
		await loadDevExtension(DEV_SERVER);
		vi.stubGlobal("window", { is_developer_mode: false });

		expect(getDevSessionExtension()).toBeUndefined();
	});
});
