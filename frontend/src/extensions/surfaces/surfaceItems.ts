/**
 * The bookkeeping every surface repeats: which extension registered what, under
 * which key, and how to take it back.
 *
 * A surface keeps only what is its own — how to read a registration, how to
 * merge a patch, and what descriptor the registry receives.
 *
 * `update` merges and registers again. A registry item is a copy
 * (`createRegistry.ts:65`), so a value held anywhere else never reaches the
 * screen, and re-registering keeps the item's slot.
 */

import type { RegistryEntry, createRegistry } from "@/utils/createRegistry";
import { bridge } from "../host/bridge";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { fields, refuse, text } from "../params";

type Named = { name: string };

export type SurfaceItem<TRegistration> = {
	extension: InstalledExtension;
	registration: TRegistration;
};

type Options<TRegistration extends Named, TItem extends RegistryEntry> = {
	/** Names the surface in a refusal, such as "left panel tab". */
	kind: string;
	registry: ReturnType<typeof createRegistry<TItem>>;
	readRegistration: (params: unknown, extension: InstalledExtension) => TRegistration;
	mergeRegistration: (
		current: TRegistration,
		patch: Record<string, unknown>,
		extension: InstalledExtension,
	) => TRegistration;
	toRegistryItem: (key: string, item: SurfaceItem<TRegistration>) => TItem;
	/** One per extension, as 1.10 requires of leftPanel and settings. */
	limitToOnePerExtension?: boolean;
};

export const createSurfaceItems = <TRegistration extends Named, TItem extends RegistryEntry>(
	options: Options<TRegistration, TItem>,
) => {
	const items = new Map<string, SurfaceItem<TRegistration> & { unregister: () => void }>();

	// the host composes every registry name: two extensions may pick the same one
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

		// registering the same one again replaces it, which is what a reloaded frame
		// does on every edit. Only a second, differently named one is refused
		const owned = [...items].some(([held, item]) => item.extension.name === extension.name && held !== key);
		if (options.limitToOnePerExtension && owned) {
			throw refuse(`"${extension.name}" already registers a ${options.kind}.`, "already_registered");
		}

		// a re-registration replaces the item, so its teardown must not be added twice
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
