/**
 * The storage of an extension. No permission gates it. It is not a write to
 * the page, so read-only mode does not stop it.
 *
 * The site keeps one JSON row for each user and installation. Before, it used
 * `localStorage`, which is per browser. Then two people on one computer shared
 * the state of each extension.
 *
 * A dev extension still uses the browser. Its installation is removed on each
 * `pagehide`. So a site row would not stay after the reload that an author needs.
 */

import { isDevExtension } from "@/extensions/devExtension";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { createResource } from "frappe-ui";
import type { MethodTable } from "../bridge/permissions";
import { fields, refuse, text } from "../bridge/params";

type Store = Record<string, unknown>;

/** A plain copy, because `createResource` returns its reactive `data`. */
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
 * Space for settings and a cached list. It is small, so that no extension fills
 * the storage of the origin that it shares with the editor. The server has the
 * same limit.
 */
const MAX_BYTES = 100_000;

/** Has a namespace, as the route variables of a page do in `pageStore.ts`. */
const keyFor = (extension: InstalledExtension) => `builder-extension:${extension.name}`;

/**
 * If the store cannot be parsed, the code treats it as empty. A broad fallback
 * is correct here. The value belongs to the extension. Without the fallback,
 * one bad entry would stop all later writes of the extension.
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
		// Builder keys use the same origin. So this can occur when an extension is
		// well inside its own limit
		throw refuse(`This browser has no room left to store "${extension.name}" state.`, "storage_full");
	}
};

const get = (_params: unknown, extension: InstalledExtension) =>
	isDevExtension(extension) ? readLocal(extension) : invoke("get_state", { extension: extension.name });

/**
 * A patch, merged at the top level. `set` never removes a key that the call
 * does not name. An extension has up to five frames. With the merge, a panel
 * that saves its query does not remove what the entry stored. The server locks
 * the row while it merges, so two frames cannot lose a write.
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
	// the storage of the extension. So these methods need no permission
	"state.get": { needs: null, run: get },
	"state.set": { needs: null, run: set },
	"state.unset": { needs: null, run: unset },
};
