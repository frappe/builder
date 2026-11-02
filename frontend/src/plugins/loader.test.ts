import { beforeEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";

vi.mock("frappe-ui", () => ({ call: vi.fn() }));

import {
	importPlugins,
	installPlugins,
	loadPlugin,
	replacePlugin,
	unloadPlugin,
	inspectPlugin,
	runningPlugins,
} from "./loader";
import { openHandlers } from "./context";

type Installed = { names: string[]; contexts: Record<string, unknown>[] };
const installed = () => (globalThis as unknown as { installed: Installed }).installed;

const moduleUrl = (source: string) => `data:text/javascript,${encodeURIComponent(source)}`;

const recordingVuePlugin = (name: string) =>
	`export default { install: (app, context) => { globalThis.installed.names.push('${name}'); globalThis.installed.contexts.push(context) } }`;

const plugin = (name: string, source: string) => ({
	name,
	label: name,
	version: "1.0.0",
	entryUrl: moduleUrl(source),
});

describe("plugins", () => {
	beforeEach(() => {
		vi.spyOn(console, "error").mockImplementation(() => {});
		(globalThis as unknown as { installed: Installed }).installed = { names: [], contexts: [] };
		runningPlugins.clear();
	});

	it("installs each entry module's default export as a Vue plugin, with its context", async () => {
		installPlugins(createApp({}), await importPlugins([plugin("acme/seo", recordingVuePlugin("seo"))]));

		expect(installed().names).toEqual(["seo"]);
		expect(installed().contexts[0]).toMatchObject({ name: "acme/seo", label: "acme/seo", version: "1.0.0" });
		expect(runningPlugins.has("acme/seo")).toBe(true);
	});

	it("skips a plugin that fails to load or install, and still installs the others", async () => {
		const loaded = await importPlugins([
			plugin("acme/broken", "throw new Error('boom')"),
			plugin("acme/no-vue-plugin", "export default 42"),
			plugin("acme/throws", "export default { install() { throw new Error('install failed') } }"),
			plugin("acme/seo", recordingVuePlugin("seo")),
		]);
		installPlugins(createApp({}), loaded);

		expect(installed().names).toEqual(["seo"]);
		expect(console.error).toHaveBeenCalledTimes(3);
	});

	it("loads one more plugin into the running app", async () => {
		installPlugins(createApp({}), []);

		await loadPlugin(plugin("acme/later", recordingVuePlugin("later")));

		expect(installed().names).toEqual(["later"]);
		expect(runningPlugins.has("acme/later")).toBe(true);
	});

	it("keeps the working plugin when replacement fails, and disposes on unload", async () => {
		installPlugins(createApp({}), []);
		const name = "acme/recoverable";
		await loadPlugin(
			plugin(
				name,
				`export default { install(app, context) { context.setOpenHandler(() => 'working'); context.onDispose(() => globalThis.installed.names.push('disposed')); } }`,
			),
		);
		const original = openHandlers.get(name);
		await expect(
			replacePlugin(
				plugin(
					name,
					`export default { install(app, context) { context.setOpenHandler(() => 'broken'); throw Error('bad candidate'); } }`,
				),
			),
		).rejects.toThrow("bad candidate");
		expect(openHandlers.get(name)).toBe(original);
		expect(installed().names).toEqual([]);
		unloadPlugin(name);
		unloadPlugin(name);
		expect(installed().names).toEqual(["disposed"]);
		expect(openHandlers.has(name)).toBe(false);
	});

	it("inspects without activating a candidate and disposes its resources", async () => {
		installPlugins(createApp({}), []);
		const candidate = plugin(
			"acme/candidate",
			`export default { install(app, context) { context.setOpenHandler(() => {}); context.onDispose(() => globalThis.installed.names.push('candidate disposed')); } }`,
		);
		const inspected = await inspectPlugin(candidate);
		expect(runningPlugins.has(candidate.name)).toBe(false);
		expect(openHandlers.has(candidate.name)).toBe(false);
		inspected.dispose();
		expect(installed().names).toEqual(["candidate disposed"]);
	});
});
