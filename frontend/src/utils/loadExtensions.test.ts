import { beforeEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";

const { installed } = vi.hoisted(() => ({ installed: { rows: [] as unknown[] } }));
vi.mock("frappe-ui", () => ({ call: () => Promise.resolve(installed.rows) }));

import { importExtensions, installExtensions } from "./loadExtensions";

const moduleUrl = (source: string) => `data:text/javascript,${encodeURIComponent(source)}`;

const extension = (name: string, source: string) => ({
	name,
	label: name,
	entry_url: moduleUrl(source),
	style_url: null,
});

describe("extensions", () => {
	beforeEach(() => {
		vi.spyOn(console, "error").mockImplementation(() => {});
		(globalThis as { installedBy?: string[] }).installedBy = [];
	});

	it("installs each entry module's default export as a Vue plugin", async () => {
		installed.rows = [
			extension("seo", "export default { install: () => globalThis.installedBy.push('seo') }"),
		];

		installExtensions(createApp({}), await importExtensions());

		expect((globalThis as { installedBy?: string[] }).installedBy).toEqual(["seo"]);
	});

	it("skips an extension that fails to load or install, and still installs the others", async () => {
		installed.rows = [
			extension("broken", "throw new Error('boom')"),
			extension("no-plugin", "export default 42"),
			extension("throws", "export default { install() { throw new Error('install failed') } }"),
			extension("seo", "export default { install: () => globalThis.installedBy.push('seo') }"),
		];

		installExtensions(createApp({}), await importExtensions());

		expect((globalThis as { installedBy?: string[] }).installedBy).toEqual(["seo"]);
		expect(console.error).toHaveBeenCalledTimes(3);
	});
});
