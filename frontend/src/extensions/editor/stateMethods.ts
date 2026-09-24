/**
 * Storage an extension owns outright. No capability gates it: the drawer
 * is not a write to the page, so a read-only page does not close it.
 *
 * One row per key, on the site. It used to be `localStorage`, which is per
 * browser, so two people sharing a machine shared every extension's state.
 *
 * A dev extension still uses the browser: its installation goes on every
 * `pagehide`, so a site row would not survive the reload an author needs.
 */

import { isDevExtension } from "@/extensions/devExtension";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { createResource } from "frappe-ui";
import type { MethodTable } from "../host/capabilities";
import { fields, refuse, text } from "../params";

type Store = Record<string, unknown>;

/** Rebuilt plain, because `createResource` answers with its reactive `data`. */
const plain = <T>(value: T): T => JSON.parse(JSON.stringify(value ?? null));

const invoke = (method: string, params: Record<string, unknown>) =>
	createResource({ url: `builder.extensions.state.${method}` })
		.submit(params)
		.then(plain)
		.catch((thrown: unknown) => {
			const sent = thrown as { messages?: string[]; message?: string };
			throw refuse(sent.messages?.[0] || sent.message || "The server refused that call.", "server_error");
		});

/**
 * Room for settings and a cached list, small enough that no extension fills the
 * origin the editor shares with it. The server holds the same ceiling.
 */
const MAX_BYTES = 100_000;

/** Namespaced, the way `pageStore.ts:63` namespaces a page's route variables. */
const keyFor = (extension: InstalledExtension) => `builder-extension:${extension.name}`;

/**
 * A store that will not parse is treated as absent. A broad fallback is right
 * here. The value is the extension's own, and one bad entry would otherwise stop
 * the extension writing ever again.
 */
const readLocal = (extension: InstalledExtension): Store => {
	const stored = localStorage.getItem(keyFor(extension));
	if (!stored) return {};

	try {
		const parsed = JSON.parse(stored);
		return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
	} catch {
		console.warn(`Extension "${extension.name}" had unreadable state, which was dropped.`);
		return {};
	}
};

const writeLocal = (extension: InstalledExtension, store: Store) => {
	const serialized = JSON.stringify(store);
	if (serialized.length > MAX_BYTES) {
		throw refuse(`"${extension.name}" state is larger than ${MAX_BYTES / 1000} kB.`, "state_too_large");
	}

	try {
		localStorage.setItem(keyFor(extension), serialized);
	} catch {
		// the origin is shared with Builder's own keys, so this can happen to an
		// extension that stayed well inside its own limit
		throw refuse(`This browser has no room left to store "${extension.name}" state.`, "storage_full");
	}
};

const get = (_params: unknown, extension: InstalledExtension) =>
	isDevExtension(extension) ? readLocal(extension) : invoke("get_state", { extension: extension.name });

/**
 * A patch, merged at the top level. `set` never removes what a call leaves
 * unmentioned. An extension has up to five frames, and merging stops a panel
 * saving its query from erasing what the entry stored. The server keeps one row
 * per key, so two writing different keys never race.
 */
const set = (params: unknown, extension: InstalledExtension) => {
	const patch = fields(params).state;
	if (typeof patch !== "object" || patch === null || Array.isArray(patch)) {
		throw refuse(`"state" must be an object.`, "invalid_params");
	}

	if (!isDevExtension(extension)) {
		return invoke("set_state", { extension: extension.name, state: patch });
	}
	writeLocal(extension, { ...readLocal(extension), ...(patch as Store) });
};

const unset = (params: unknown, extension: InstalledExtension) => {
	const key = text(fields(params).key, "key");

	if (!isDevExtension(extension)) {
		return invoke("unset_state", { extension: extension.name, key });
	}
	const store = readLocal(extension);
	delete store[key];
	writeLocal(extension, store);
};

export const stateMethods: MethodTable = {
	// the extension's own drawer, so nothing here needs a grant
	"state.get": { needs: null, run: get },
	"state.set": { needs: null, run: set },
	"state.unset": { needs: null, run: unset },
};
