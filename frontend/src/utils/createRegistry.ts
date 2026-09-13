import { computed, markRaw, reactive, ref, toRaw } from "vue";

const isComponentLike = (value: unknown): value is object =>
	Boolean(value) &&
	typeof value === "object" &&
	("render" in (value as object) || "setup" in (value as object) || "__name" in (value as object));

// items live in a reactive Map, which would proxy the component definitions they
// carry (a tab's panel, a control, an icon) and make Vue warn on every render
function withRawComponents<T extends object>(item: T): T {
	for (const [key, value] of Object.entries(item)) {
		if (isComponentLike(value)) {
			(item as Record<string, unknown>)[key] = markRaw(value);
		} else if (Array.isArray(value)) {
			value.forEach((entry) => entry && typeof entry === "object" && withRawComponents(entry));
		}
	}
	return item;
}

/**
 * Every registry item needs a stable identity, and may ask for a position
 * relative to another item's name.
 *
 * An unknown `before` name puts the item first, an unknown `after` name puts it
 * last, so an extension that anchors to a feature this site does not have still
 * lands somewhere sensible.
 */
export type RegistryEntry = {
	name: string;
	before?: string;
	after?: string;
};

/** The common case: the surface itself decides whether an item shows. */
export type RegistryItem = RegistryEntry & {
	condition?: () => boolean;
};

/**
 * A registry backs one editor surface. Builder registers its own items with
 * `registerBuiltIn`, which locks the name. Extensions use `register`, and cannot
 * replace or remove a built-in item.
 *
 * Leave `before` and `after` unset in the common case: items then display in
 * registration order.
 *
 * Read `visible` when an item decides its own visibility. Read `all` when the
 * surface passes an argument to condition, as the block context menu does.
 */
export function createRegistry<T extends RegistryEntry>() {
	const items = reactive(new Map<string, T>()) as Map<string, T>;
	const builtInNames = new Set<string>();
	const order = ref<string[]>([]);

	// re-registering without an anchor keeps the slot the name already holds, so
	// installing the same set twice cannot reshuffle the surface
	const place = (item: T) => {
		const current = order.value.indexOf(item.name);
		if (current !== -1) {
			if (!item.before && !item.after) return;
			order.value.splice(current, 1);
		}
		if (item.before) {
			const anchor = order.value.indexOf(item.before);
			order.value.splice(anchor === -1 ? 0 : anchor, 0, item.name);
		} else if (item.after) {
			const anchor = order.value.indexOf(item.after);
			if (anchor === -1) order.value.push(item.name);
			else order.value.splice(anchor + 1, 0, item.name);
		} else {
			order.value.push(item.name);
		}
	};

	const remove = (name: string) => {
		const position = order.value.indexOf(name);
		if (position !== -1) order.value.splice(position, 1);
		return items.delete(name);
	};

	const add = (item: T) => {
		// Registry entries can carry Vue components. Keeping the snapshot raw stops
		// the reactive Map from proxying those components before a surface renders it.
		const registered = withRawComponents({ ...item });
		items.set(item.name, registered);
		place(registered);
		// a later registration under the same name owns the entry, so this must not delete it
		return () => {
			if (toRaw(items.get(item.name)) === registered) remove(item.name);
		};
	};

	const guardBuiltIn = (name: string) => {
		if (builtInNames.has(name)) throw new Error(`"${name}" is a built-in item and is read-only`);
	};

	/** Builder registers its own items here. A built-in name is then locked. */
	const registerBuiltIn = (item: T) => {
		builtInNames.add(item.name);
		return add(item);
	};

	// returns its own unregister, so a caller never has to track names
	const register = (item: T) => {
		guardBuiltIn(item.name);
		return add(item);
	};

	const unregister = (name: string) => {
		guardBuiltIn(name);
		return remove(name);
	};

	const all = computed(() => order.value.map((name) => items.get(name) as T));

	// condition runs at render, never at register, so it can read live state
	const visible = computed(() => all.value.filter((item) => (item as RegistryItem).condition?.() ?? true));

	return { register, registerBuiltIn, unregister, all, visible };
}
