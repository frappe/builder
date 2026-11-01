// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { sanitizeLayoutSVG } from "./cardPreview";

describe("layout option previews", () => {
	it("renders static layout structure and labels", () => {
		const svg = sanitizeLayoutSVG(
			'<svg viewBox="0 0 100 60"><rect width="100" height="60" fill="#eee"/><text x="10" y="20">Bakery</text></svg>',
		);
		expect(svg).toContain('viewBox="0 0 100 60"');
		expect(svg).toContain("Bakery");
		expect(svg).toContain('fill="#eee"');
	});
	it("removes scripts, events, foreign HTML, links and remote paint", () => {
		const svg = sanitizeLayoutSVG(
			'<svg onload="alert(1)"><script>alert(1)</script><foreignObject><div>HTML</div></foreignObject><image href="https://remote/image"/><use href="https://remote/icon"/><rect style="fill:red" fill="url(https://remote/paint)" onclick="alert(1)"/><animate attributeName="href" values="javascript:alert(1)"/></svg>',
		);
		for (const forbidden of [
			"script",
			"onload",
			"onclick",
			"foreignObject",
			"remote",
			"style=",
			"animate",
			"<use",
			"<image",
		])
			expect(svg).not.toContain(forbidden);
	});
});
