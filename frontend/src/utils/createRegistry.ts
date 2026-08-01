import { computed, reactive } from "vue";

/** Every registry item needs a stable identity and a sort position. */
export type Identified = {
	name: string;
	rank?: number;
};

/** The common case: the surface itself decides whether an item shows. */
export type RegistryItem = Identified & {
	condition?: () => boolean;
};

const RANK_STEP = 10;

/**
 * A registry backs one editor surface. Built-in features and, later, extensions
 * register through the same function.
 *
 * Leave `rank` unset in the common case: items then display in registration order.
 * Set it only to force an item to a specific spot (e.g. ahead of, or behind, an
 * item registered earlier).
 *
 * Read `visible` when an item decides its own visibility. Read `all` when the
 * surface passes an argument to condition, as the block context menu does.
 */
export function createRegistry<T extends Identified>() {
	const items = reactive(new Map<string, T>()) as Map<string, T>;
	let nextAutoRank = RANK_STEP;

	// returns its own unregister, so a caller never has to track names
	const register = (item: T) => {
		const rank = item.rank ?? nextAutoRank;
		nextAutoRank = Math.max(nextAutoRank, rank + RANK_STEP);
		items.set(item.name, { ...item, rank });
		return () => items.delete(item.name);
	};

	const unregister = (name: string) => items.delete(name);

	const all = computed(() => [...items.values()].sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0)));

	// condition runs at render, never at register, so it can read live state
	const visible = computed(() => all.value.filter((item) => (item as RegistryItem).condition?.() ?? true));

	return { register, unregister, all, visible };
}
