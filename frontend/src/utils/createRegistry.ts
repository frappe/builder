import { computed, reactive } from "vue";

export type RegistryItem = {
	name: string;
	rank?: number;
	condition?: () => boolean;
};

const DEFAULT_RANK = 100;

/**
 * A registry backs one editor surface. Built-in features and, later, extensions
 * register through the same function.
 */
export function createRegistry<T extends RegistryItem>() {
	const items = reactive(new Map<string, T>()) as Map<string, T>;

	// returns its own unregister, so a caller never has to track names
	const register = (item: T) => {
		items.set(item.name, item);
		return () => items.delete(item.name);
	};

	const unregister = (name: string) => items.delete(name);

	// condition runs at render, never at register, so it can read live state
	const visible = computed(() =>
		[...items.values()]
			.filter((item) => item.condition?.() ?? true)
			.sort((a, b) => (a.rank ?? DEFAULT_RANK) - (b.rank ?? DEFAULT_RANK)),
	);

	return { register, unregister, visible };
}
