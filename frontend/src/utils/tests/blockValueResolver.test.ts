import { describe, expect, it, vi } from "vitest";

vi.mock("@/utils/helpers", () => ({
	getDataForKey: (data: Record<string, unknown>, key: string) => data[key],
	getParentProps: () => ({}),
	getPropValue: () => undefined,
}));
vi.mock("@/extensions/editor/safeMarkup", () => ({
	sanitizeHTML: (html: string) => html.replace(/ onerror="[^"]*"/, ""),
	isSafeBoundAttribute: (element: string, name: string, value: string) => !value.startsWith("javascript:"),
}));

import { BlockValueResolver } from "../blockValueResolver";

const resolverFor = (dynamicValues: BlockDataKey[], data: Record<string, unknown>) =>
	new BlockValueResolver({
		block: () =>
			({
				getElement: () => "a",
				getDataKey: () => undefined,
				getDynamicValues: () => dynamicValues,
				getBlockProps: () => ({}),
			}) as any,
		data: () => data,
		componentData: () => null,
		defaultProps: () => null,
	});

describe("bound values in the canvas", () => {
	it("sanitizes bound inner HTML", () => {
		const resolver = resolverFor([{ key: "body", type: "key", property: "innerHTML" }], {
			body: '<img src="x" onerror="alert(1)">',
		});
		expect(resolver.applyDynamicValues("key", { innerHTML: null }).innerHTML).toBe('<img src="x">');
	});

	it("drops an unsafe bound attribute and keeps the attribute it would replace", () => {
		const resolver = resolverFor(
			[
				{ key: "link", type: "attribute", property: "href" },
				{ key: "label", type: "attribute", property: "title" },
			],
			{ link: "javascript:alert(1)", label: "Read more" },
		);
		const attributes = resolver.applyDynamicValues("attribute", { href: "/blog", block: "kept" });
		expect(attributes).toEqual({ href: "/blog", title: "Read more", block: "kept" });
	});
});
