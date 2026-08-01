import { ref } from "vue";
import { describe, expect, it } from "vitest";
import { createRegistry, type RegistryItem } from "./createRegistry";

type TestItem = RegistryItem & { label?: string };

const names = (items: readonly TestItem[]) => items.map((item) => item.name);

describe("createRegistry", () => {
	it("sorts by rank", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "c", rank: 30 });
		registry.register({ name: "a", rank: 10 });
		registry.register({ name: "b", rank: 20 });

		expect(names(registry.visible.value)).toEqual(["a", "b", "c"]);
	});

	it("keeps registration order when ranks tie", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "first", rank: 10 });
		registry.register({ name: "second", rank: 10 });

		expect(names(registry.visible.value)).toEqual(["first", "second"]);
	});

	it("gives an item with no rank the default rank", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "ranked-after", rank: 200 });
		registry.register({ name: "unranked" });
		registry.register({ name: "ranked-before", rank: 10 });

		expect(names(registry.visible.value)).toEqual(["ranked-before", "unranked", "ranked-after"]);
	});

	it("hides an item whose condition is false", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "shown", rank: 10 });
		registry.register({ name: "hidden", rank: 20, condition: () => false });

		expect(names(registry.visible.value)).toEqual(["shown"]);
	});

	// visible is a computed, so a condition has to read reactive state to re-run
	it("re-runs the condition when the reactive state it reads changes", () => {
		const registry = createRegistry<TestItem>();
		const allowed = ref(false);
		registry.register({ name: "gated", condition: () => allowed.value });

		expect(names(registry.visible.value)).toEqual([]);

		allowed.value = true;
		expect(names(registry.visible.value)).toEqual(["gated"]);
	});

	it("returns an unregister function from register", () => {
		const registry = createRegistry<TestItem>();
		const remove = registry.register({ name: "temporary" });

		expect(names(registry.visible.value)).toEqual(["temporary"]);

		remove();
		expect(names(registry.visible.value)).toEqual([]);
	});

	it("unregisters by name", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "keep", rank: 10 });
		registry.register({ name: "drop", rank: 20 });

		expect(registry.unregister("drop")).toBe(true);
		expect(registry.unregister("never-registered")).toBe(false);
		expect(names(registry.visible.value)).toEqual(["keep"]);
	});

	it("replaces an item registered under the same name", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "tab", label: "old" });
		registry.register({ name: "tab", label: "new" });

		expect(registry.visible.value).toHaveLength(1);
		expect(registry.visible.value[0].label).toBe("new");
	});
});
