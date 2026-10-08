import { describe, expect, it } from "vitest";
import { settingsItems } from "../index";

describe("settings registry", () => {
	// prefetchBuilderSettings loads each pane early. A pane without `load` loads late on first open.
	it("gives every pane a loader", () => {
		const items = settingsItems.all.value;

		expect(items.length).toBeGreaterThan(0);
		items.forEach((item) => expect(typeof item.load).toBe("function"));
	});

	it("builds a component from the loader", () => {
		settingsItems.all.value.forEach((item) => expect(item.component).toBeTruthy());
	});

	// The analytics panes use the largest chunk. So the prefetch does not load them.
	it("keeps the analytics panes out of the prefetch", () => {
		const skipped = settingsItems.all.value.filter((item) => item.preload === false);

		expect(skipped.map((item) => item.name)).toEqual(["page_analytics", "global_analytics"]);
	});
});
