import { ref } from "vue";
import { describe, expect, it } from "vitest";
import { createRegistry, type RegistryItem } from "./createRegistry";

type TestItem = RegistryItem & { label?: string };

const names = (items: readonly TestItem[]) => items.map((item) => item.name);

describe("createRegistry", () => {
	it("keeps registration order for items with no anchor", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "first" });
		registry.register({ name: "second" });
		registry.register({ name: "third" });

		expect(names(registry.visible.value)).toEqual(["first", "second", "third"]);
	});

	it("inserts before a registered name", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "a" });
		registry.register({ name: "c" });
		registry.register({ name: "b", before: "c" });

		expect(names(registry.visible.value)).toEqual(["a", "b", "c"]);
	});

	it("inserts after a registered name", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "a" });
		registry.register({ name: "c" });
		registry.register({ name: "b", after: "a" });

		expect(names(registry.visible.value)).toEqual(["a", "b", "c"]);
	});

	it("puts an item first when its before name is not registered", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "a" });
		registry.register({ name: "b" });
		registry.register({ name: "orphan", before: "missing" });

		expect(names(registry.visible.value)).toEqual(["orphan", "a", "b"]);
	});

	it("puts an item last when its after name is not registered", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "a" });
		registry.register({ name: "b" });
		registry.register({ name: "orphan", after: "missing" });

		expect(names(registry.visible.value)).toEqual(["a", "b", "orphan"]);
	});

	it("hides an item whose condition is false", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "shown" });
		registry.register({ name: "hidden", condition: () => false });

		expect(names(registry.visible.value)).toEqual(["shown"]);
	});

	it("keeps a condition-hidden item in all, so a surface can apply its own filter", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "shown" });
		registry.register({ name: "hidden", condition: () => false });

		expect(names(registry.all.value)).toEqual(["shown", "hidden"]);
	});

	it("orders all the same way as visible", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "late" });
		registry.register({ name: "early", before: "late" });

		expect(names(registry.all.value)).toEqual(["early", "late"]);
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
		registry.register({ name: "keep" });
		registry.register({ name: "drop" });

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

	// two surfaces install the same built-in set, so this must not reshuffle
	it("keeps an item in its slot when the same set registers twice", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "a" });
		registry.register({ name: "b" });
		registry.register({ name: "extension" });

		registry.register({ name: "a" });
		registry.register({ name: "b" });

		expect(names(registry.visible.value)).toEqual(["a", "b", "extension"]);
	});

	it("moves an item when it registers again with an anchor", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "a" });
		registry.register({ name: "b" });
		registry.register({ name: "b", before: "a" });

		expect(names(registry.visible.value)).toEqual(["b", "a"]);
	});

	it("keeps a replacement when the replaced registration unregisters", () => {
		const registry = createRegistry<TestItem>();
		const removeOld = registry.register({ name: "tab", label: "old" });
		registry.register({ name: "tab", label: "new" });

		removeOld();
		expect(names(registry.visible.value)).toEqual(["tab"]);
		expect(registry.visible.value[0].label).toBe("new");
	});
});
