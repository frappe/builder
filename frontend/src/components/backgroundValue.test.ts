import { describe, expect, it, vi } from "vitest";

vi.mock("@/utils/helpers", () => ({ cssUrl: (url: string) => `url("${url}")` }));

import { parseBackgroundValue } from "./backgroundValue";

vi.stubGlobal("CSS", {
	supports: (property: string, value: string) => {
		if (property === "color") return /^(#[0-9a-f]{3,8}|red|blue)$/i.test(value);
		return /^(var\(|linear-gradient\(|url\()/i.test(value);
	},
});

describe("background input", () => {
	it("keeps an unresolved variable as a background shorthand", () => {
		expect(parseBackgroundValue("var(--HeroSurface)", "var(--HeroSurface)")).toEqual({
			background: "var(--HeroSurface)",
		});
	});

	it("uses the color control for a known color token", () => {
		expect(parseBackgroundValue("var(--brand-color)", "#abc123")).toEqual({
			color: "var(--brand-color)",
		});
	});

	it("retains layered image CSS and handles a plain URL", () => {
		expect(parseBackgroundValue('url("/hero.webp") center / cover', "")).toEqual({
			background: 'url("/hero.webp") center / cover',
		});
		expect(parseBackgroundValue('url("/hero.webp")', "")).toEqual({
			image: 'url("/hero.webp")',
		});
	});

	it("routes a gradient to the gradient editor", () => {
		expect(parseBackgroundValue("linear-gradient(red, blue)", "")).toEqual({
			image: "linear-gradient(red, blue)",
		});
	});
});
