import { describe, expect, it, vi } from "vitest";

// DOMPurify knows `href` and `title`, refuses a javascript: URL, and does not know `darkSrc`
vi.mock("dompurify", () => ({
	default: () => ({
		setConfig: () => {},
		isValidAttribute: (element: string, name: string, value: string) =>
			["href", "title"].includes(name) && !value.startsWith("javascript:"),
	}),
}));

// the module makes its DOMPurify instance from `window` when it loads
vi.hoisted(() => vi.stubGlobal("window", {}));
import { isSafeBoundAttribute } from "../safeMarkup";

describe("bound attributes", () => {
	it("refuses attributes that run code", () => {
		expect(isSafeBoundAttribute("img", "onerror", "alert(1)")).toBe(false);
		expect(isSafeBoundAttribute("iframe", "srcdoc", "<script></script>")).toBe(false);
		expect(isSafeBoundAttribute("a", "href", "javascript:alert(1)")).toBe(false);
	});

	it("keeps safe values and names DOMPurify does not know", () => {
		expect(isSafeBoundAttribute("a", "href", "/blog/post")).toBe(true);
		expect(isSafeBoundAttribute("img", "darkSrc", "/dark.png")).toBe(true);
	});
});
