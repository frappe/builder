import { beforeEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";

vi.mock("frappe-ui", () => ({ call: vi.fn() }));

import { importExtensions, installExtensions, loadExtension, runningExtensions } from "./loader";

type Installed = { names: string[]; contexts: Record<string, unknown>[] };
const installed = () => (globalThis as unknown as { installed: Installed }).installed;

const moduleUrl = (source: string) => `data:text/javascript,${encodeURIComponent(source)}`;

const recordingPlugin = (name: string) =>
	`export default { install: (app, context) => { globalThis.installed.names.push('${name}'); globalThis.installed.contexts.push(context) } }`;

const extension = (name: string, source: string) => ({
	name,
	label: name,
	version: "1.0.0",
	entryUrl: moduleUrl(source),
});

describe("extensions", () => {
	beforeEach(() => {
		vi.spyOn(console, "error").mockImplementation(() => {});
		(globalThis as unknown as { installed: Installed }).installed = { names: [], contexts: [] };
		runningExtensions.clear();
	});

	it("installs each entry module's default export as a Vue plugin, with its context", async () => {
		installExtensions(createApp({}), await importExtensions([extension("acme/seo", recordingPlugin("seo"))]));

		expect(installed().names).toEqual(["seo"]);
		expect(installed().contexts[0]).toMatchObject({ name: "acme/seo", label: "acme/seo", version: "1.0.0" });
		expect(runningExtensions.has("acme/seo")).toBe(true);
	});

	it("skips an extension that fails to load or install, and still installs the others", async () => {
		const loaded = await importExtensions([
			extension("acme/broken", "throw new Error('boom')"),
			extension("acme/no-plugin", "export default 42"),
			extension("acme/throws", "export default { install() { throw new Error('install failed') } }"),
			extension("acme/seo", recordingPlugin("seo")),
		]);
		installExtensions(createApp({}), loaded);

		expect(installed().names).toEqual(["seo"]);
		expect(console.error).toHaveBeenCalledTimes(3);
	});

	it("loads one more extension into the running app", async () => {
		installExtensions(createApp({}), []);

		await loadExtension(extension("acme/later", recordingPlugin("later")));

		expect(installed().names).toEqual(["later"]);
		expect(runningExtensions.has("acme/later")).toBe(true);
	});
});
