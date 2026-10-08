/**
 * Records which extension added each item, and removes the items.
 * `update` merges the changes and registers the item again. The item keeps its position.
 */

import type { RegistryEntry, createRegistry } from "@/utils/createRegistry";
import { bridge } from "../bridge/bridge";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { fields, refuse, text } from "../bridge/params";

type Named = { name: string };

export type SurfaceItem<TRegistration> = {
	extension: InstalledExtension;
	registration: TRegistration;
};

type Options<TRegistration extends Named, TItem extends RegistryEntry> = {
	/** The name of the surface in an error, for example "toolbar item". */
	kind: string;
	registry: ReturnType<typeof createRegistry<TItem>>;
	readRegistration: (params: unknown, extension: InstalledExtension) => TRegistration;
	mergeRegistration: (
		current: TRegistration,
		patch: Record<string, unknown>,
		extension: InstalledExtension,
	) => TRegistration;
	toRegistryItem: (key: string, item: SurfaceItem<TRegistration>) => TItem;
};

export const createSurfaceItems = <TRegistration extends Named, TItem extends RegistryEntry>(
	options: Options<TRegistration, TItem>,
) => {
	const items = new Map<string, SurfaceItem<TRegistration> & { unregister: () => void }>();

	// The host makes each registry name. Two extensions can use the same key.
	const createItemKey = (extension: InstalledExtension, name: string) => `${extension.name}:${name}`;

	const readItemKey = (params: unknown, extension: InstalledExtension) =>
		createItemKey(extension, text(fields(params).name, "name"));

	const getRegisteredItem = (key: string) => {
		const item = items.get(key);
		if (!item) throw refuse(`No ${options.kind} is registered under "${key}".`, "unknown_item");
		return item;
	};

	const upsertRegistryItem = (key: string, item: SurfaceItem<TRegistration>) => {
		const unregister = options.registry.register(options.toRegistryItem(key, item));
		items.set(key, { ...item, unregister });
	};

	const unregisterItem = (key: string) => {
		items.get(key)?.unregister();
		items.delete(key);
	};

	const register = (params: unknown, extension: InstalledExtension) => {
		const registration = options.readRegistration(params, extension);
		const key = createItemKey(extension, registration.name);

		// A second registration replaces the item. Do not add its teardown again.
		if (!items.has(key)) bridge.registerTeardown(extension.name, () => unregisterItem(key));
		upsertRegistryItem(key, { extension, registration });
	};

	const update = (params: unknown, extension: InstalledExtension) => {
		const key = readItemKey(params, extension);
		const item = getRegisteredItem(key);
		upsertRegistryItem(key, {
			extension: item.extension,
			registration: options.mergeRegistration(item.registration, fields(fields(params).patch), extension),
		});
	};

	const unregister = (params: unknown, extension: InstalledExtension) => {
		const key = readItemKey(params, extension);
		getRegisteredItem(key);
		unregisterItem(key);
	};

	return { register, update, unregister };
};
