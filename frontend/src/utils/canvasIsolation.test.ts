import { describe, expect, it, vi } from "vitest";

vi.mock("dompurify", () => ({ default: () => ({ addHook: vi.fn(), sanitize: (html: string) => html }) }));
vi.mock("@/data/builderSettings", () => ({ builderSettings: { doc: null } }));
// the module hands the window to DOMPurify when it loads
vi.stubGlobal("window", { location: { href: "https://frappe.page/builder", origin: "https://frappe.page" } });

const importIsolated = async (isIsolated: boolean) => {
	vi.resetModules();
	vi.doMock("@/utils/frappePage", () => ({ isIsolated }));
	return import("./canvasIsolation");
};

describe("canvasTag", () => {
	it("draws an active element as a div on frappe.page", async () => {
		const { canvasTag } = await importIsolated(true);

		expect(["script", " Object ", "embed", "base", "meta"].map(canvasTag)).toEqual(Array(5).fill("div"));
		expect(["section", "img", "iframe"].map(canvasTag)).toEqual(["section", "img", "iframe"]);
	});

	it("keeps every element elsewhere", async () => {
		const { canvasTag } = await importIsolated(false);

		expect(canvasTag("script")).toBe("script");
	});
});

describe("an isolated canvas", () => {
	const attributes = () => ({ onclick: "steal()", href: "javascript:steal()", title: "kept" });

	it("drops what would run from a block's attributes, and never runs block scripts", async () => {
		const { blockScriptsMode, isolateBlockAttributes } = await importIsolated(true);
		const blockAttributes = attributes();

		isolateBlockAttributes("a", blockAttributes, {});

		expect(blockAttributes).toEqual({ title: "kept" });
		expect(blockScriptsMode()).toBe("Don't Execute");
	});

	it("keeps attributes and the site's script setting when not isolated", async () => {
		const { blockScriptsMode, isolateBlockAttributes } = await importIsolated(false);
		const blockAttributes = attributes();

		isolateBlockAttributes("a", blockAttributes, {});

		expect(blockAttributes).toEqual(attributes());
		expect(blockScriptsMode()).toBe("Restricted");
	});
});
