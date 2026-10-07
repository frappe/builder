/**
 * The record keeping that each surface needs. It records which extension
 * registered an item, with which key. It also removes the item.
 *
 * A surface keeps only its own parts. These are how to read a registration,
 * how to merge a patch, and which descriptor goes to the registry.
 *
 * `update` merges and registers again. `createRegistry.ts` keeps a copy of each
 * item. So a change to a value in a different place does not show. A second
 * registration keeps the position of the item.
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
	/** The name of the surface in a refusal, for example "left panel tab". */
	kind: string;
	registry: ReturnType<typeof createRegistry<TItem>>;
	readRegistration: (params: unknown, extension: InstalledExtension) => TRegistration;
	mergeRegistration: (
		current: TRegistration,
		patch: Record<string, unknown>,
		extension: InstalledExtension,
	) => TRegistration;
	toRegistryItem: (key: string, item: SurfaceItem<TRegistration>) => TItem;
	/** Allow only one item for each extension. The left panel and settings use this. */
	limitToOnePerExtension?: boolean;
};

export const createSurfaceItems = <TRegistration extends Named, TItem extends RegistryEntry>(
	options: Options<TRegistration, TItem>,
) => {
	const items = new Map<string, SurfaceItem<TRegistration> & { unregister: () => void }>();

	// the host makes each registry name. Two extensions can choose the same name
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

		// a second registration with the same name replaces the item. A reloaded frame
		// does this on each edit. Only an item with a different name is refused
		const owned = [...items].some(([held, item]) => item.extension.name === extension.name && held !== key);
		if (options.limitToOnePerExtension && owned) {
			throw refuse(`"${extension.name}" already registers a ${options.kind}.`, "already_registered");
		}

		// a second registration replaces the item. Do not add its teardown two times
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
