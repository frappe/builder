import { beforeEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";

vi.mock("frappe-ui", () => ({ call: vi.fn() }));

import { createRegistry } from "@/utils/createRegistry";
import {
	getRunningEntry,
	importPlugins,
	installPlugins,
	loadPlugin,
	replacePlugin,
	runningPlugins,
	unloadPlugin,
} from "./loader";

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

	it("replaces a running plugin with its new version, taking back what the old one registered", async () => {
		const registry = createRegistry<{ name: string }>();
		(globalThis as unknown as { registry: typeof registry }).registry = registry;
		const registering = (name: string) =>
			`export default { install: () => globalThis.registry.register({ name: '${name}' }) }`;
		installPlugins(createApp({}), []);
		await loadPlugin(plugin("bob/tabs", registering("old-tab")));

		const next = plugin("bob/tabs", registering("new-tab"));
		await replacePlugin(next);

		expect(registry.all.value.map((item) => item.name)).toEqual(["new-tab"]);
		expect(getRunningEntry("bob/tabs")).toBe(next.entryUrl);

		unloadPlugin("bob/tabs");
		expect(registry.all.value).toEqual([]);
		expect(runningPlugins.has("bob/tabs")).toBe(false);
	});

	it("goes back to a release this page already ran", async () => {
		const registry = createRegistry<{ name: string }>();
		(globalThis as unknown as { registry: typeof registry }).registry = registry;
		const registering = (name: string) =>
			`export default { install: () => globalThis.registry.register({ name: '${name}' }) }`;
		const shared = plugin("bob/back", registering("shared-tab"));
		installPlugins(createApp({}), []);
		await loadPlugin(shared);
		await replacePlugin(plugin("bob/back", registering("draft-tab")));

		await replacePlugin(shared);

		expect(registry.all.value.map((item) => item.name)).toEqual(["shared-tab"]);
	});

	it("keeps the old version running when the new one fails to import", async () => {
		const registry = createRegistry<{ name: string }>();
		(globalThis as unknown as { registry: typeof registry }).registry = registry;
		installPlugins(createApp({}), []);
		await loadPlugin(
			plugin("bob/kept", "export default { install: () => globalThis.registry.register({ name: 'kept' }) }"),
		);

		await expect(replacePlugin(plugin("bob/kept", "export default {"))).rejects.toThrow();

		expect(registry.all.value.map((item) => item.name)).toEqual(["kept"]);
	});
});
