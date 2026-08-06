import { describe, expect, it } from "vitest";
import { settingsItems } from "./index";

describe("settings registry", () => {
	// prefetchBuilderSettings warms the panes through load, so a pane without one
	// silently keeps its chunk miss on first open
	it("gives every pane a loader", () => {
		const items = settingsItems.all.value;

		expect(items.length).toBeGreaterThan(0);
		items.forEach((item) => expect(typeof item.load).toBe("function"));
	});

	it("builds a component from the loader", () => {
		settingsItems.all.value.forEach((item) => expect(item.component).toBeTruthy());
	});

	// the analytics panes share the largest chunk we ship, so the idle prefetch skips them
	it("keeps the analytics panes out of the prefetch", () => {
		const skipped = settingsItems.all.value.filter((item) => item.preload === false);

		expect(skipped.map((item) => item.name)).toEqual(["page_analytics", "global_analytics"]);
	});
});
