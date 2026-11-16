import { describe, expect, it, vi } from "vitest";

vi.mock("frappe-ui", () => ({ call: vi.fn() }));
vi.mock("@/utils/frappePage", () => ({ isMounted: true }));

import type { PluginSource } from "./context";
import { importPlugins } from "./loader";

const plugin = (source?: PluginSource) => ({
	name: `acme/${source ?? "unknown"}`,
	label: source ?? "unknown",
	version: "1.0.0",
	entryUrl: `data:text/javascript,${encodeURIComponent("export default { install() {} }")}`,
	source,
});

describe("plugins on frappe.page", () => {
	it("loads plugins from the Hub or an app, and no others", async () => {
		vi.spyOn(console, "error").mockImplementation(() => {});
		const sources: (PluginSource | undefined)[] = ["Hub", "App", "Development", "Bob", undefined];

		const loaded = await importPlugins(sources.map(plugin));

		expect(loaded.map(({ plugin }) => plugin.source)).toEqual(["Hub", "App"]);
	});
});
