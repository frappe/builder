import { computed, markRaw, reactive, ref, toRaw } from "vue";

/**
 * A registry item has a stable name, and can ask for a position next to another item.
 * An unknown `before` name puts the item first. An unknown `after` name puts it last.
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
 * A registry keeps the items of one editor surface. Extensions cannot replace or remove a built-in item.
 * Without `before` and `after`, items show in registration order. Read `all` if the surface gives `condition` an argument.
 */
export function createRegistry<T extends RegistryEntry>() {
	const items = reactive(new Map<string, T>()) as Map<string, T>;
	const builtInNames = new Set<string>();
	const order = ref<string[]>([]);

	// An item without `before` or `after` keeps its position when it registers again.
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
		// Entries can have Vue components. A raw snapshot stops the reactive Map from wrapping them.
		const registered = markRaw({ ...item });
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

	/** Builder registers its own items here. An extension cannot use a built-in name. */
	const registerBuiltIn = (item: T) => {
		builtInNames.add(item.name);
		return add(item);
	};

	// Returns its own unregister function. So a caller does not keep the names.
	const register = (item: T) => {
		guardBuiltIn(item.name);
		return add(item);
	};

	const unregister = (name: string) => {
		guardBuiltIn(name);
		return remove(name);
	};

	/** Builder removes its own items here. The editor demo uses it. */
	const unregisterBuiltIn = (name: string) => {
		builtInNames.delete(name);
		return remove(name);
	};

	const all = computed(() => order.value.map((name) => items.get(name) as T));

	// condition runs at render, never at register, so it can read live state
	const visible = computed(() => all.value.filter((item) => (item as RegistryItem).condition?.() ?? true));

	return { register, registerBuiltIn, unregister, unregisterBuiltIn, all, visible };
}
