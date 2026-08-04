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

	it("keeps registration order for unranked items", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "first" });
		registry.register({ name: "second" });
		registry.register({ name: "third" });

		expect(names(registry.visible.value)).toEqual(["first", "second", "third"]);
	});

	it("lets an explicit rank jump an item ahead of unranked items registered earlier", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "unranked-first" });
		registry.register({ name: "jumps-to-front", rank: 1 });

		expect(names(registry.visible.value)).toEqual(["jumps-to-front", "unranked-first"]);
	});

	it("keeps later unranked items after an explicit rank set earlier", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "ranked", rank: 200 });
		registry.register({ name: "unranked" });

		expect(names(registry.visible.value)).toEqual(["ranked", "unranked"]);
	});

	it("hides an item whose condition is false", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "shown", rank: 10 });
		registry.register({ name: "hidden", rank: 20, condition: () => false });

		expect(names(registry.visible.value)).toEqual(["shown"]);
	});

	it("keeps a condition-hidden item in all, so a surface can apply its own filter", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "shown", rank: 10 });
		registry.register({ name: "hidden", rank: 20, condition: () => false });

		expect(names(registry.all.value)).toEqual(["shown", "hidden"]);
	});

	it("sorts all by rank, like visible", () => {
		const registry = createRegistry<TestItem>();
		registry.register({ name: "late", rank: 30 });
		registry.register({ name: "early", rank: 10 });

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

	it("keeps a replacement when the replaced registration unregisters", () => {
		const registry = createRegistry<TestItem>();
		const removeOld = registry.register({ name: "tab", label: "old" });
		registry.register({ name: "tab", label: "new" });

		removeOld();
		expect(names(registry.visible.value)).toEqual(["tab"]);
		expect(registry.visible.value[0].label).toBe("new");
	});
});
