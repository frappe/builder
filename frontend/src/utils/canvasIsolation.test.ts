import { describe, expect, it, vi } from "vitest";

vi.mock("dompurify", () => ({ default: () => ({ addHook: vi.fn(), sanitize: (html: string) => html }) }));
vi.mock("@/data/builderSettings", () => ({ builderSettings: { doc: null } }));
// the module hands the window to DOMPurify when it loads
vi.stubGlobal("window", {});

const importMounted = async (isMounted: boolean) => {
	vi.resetModules();
	vi.doMock("@/utils/frappePage", () => ({ isMounted }));
	return import("./canvasIsolation");
};

describe("canvasTag", () => {
	it("draws an active element as a div on frappe.page", async () => {
		const { canvasTag } = await importMounted(true);

		expect(["script", " Object ", "embed", "base", "meta"].map(canvasTag)).toEqual(Array(5).fill("div"));
		expect(["section", "img", "iframe"].map(canvasTag)).toEqual(["section", "img", "iframe"]);
	});

	it("keeps every element elsewhere", async () => {
		const { canvasTag } = await importMounted(false);

		expect(canvasTag("script")).toBe("script");
	});
});
