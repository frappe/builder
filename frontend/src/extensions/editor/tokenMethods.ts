/**
 * Design tokens an extension creates at runtime.
 *
 * The only write in this milestone that leaves the browser. `block.update`
 * mutates the block tree in memory, and `state.set` writes `localStorage`. A
 * token has to exist server-side, because `Builder Token` feeds
 * `/builder_assets/tokens.css`, which the **published** site serves — and an
 * extension's frame never runs there.
 *
 * So these resolve only once the Frappe method returns, and a frame awaiting one
 * is waiting on a round trip.
 *
 * There is no manifest field for a token list. A palette is computed from
 * something the user picks after install, so there is no fixed list a manifest
 * could hold.
 */

import { createResource } from "frappe-ui";
import builderTokens from "@/data/builderToken";
import type { MethodTable } from "../host/capabilities";
import { fields, refuse, text } from "../params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

const TOKEN_TYPES = ["Color", "Dimension", "Font"] as const;

/** One-shot, the way `router.ts:31` and `usersInfo.ts:64` call a whitelisted method. */
const invoke = (url: string, params: Record<string, unknown>) => createResource({ url }).submit(params);

/**
 * `key` is the extension's own stable id, because `Builder Token.name` is a
 * database-assigned uuid the extension never sees. Everything else is what
 * the doctype holds.
 */
const readToken = (value: unknown) => {
	const sent = fields(value);
	const type = sent.type;
	if (!TOKEN_TYPES.includes(type as (typeof TOKEN_TYPES)[number])) {
		throw refuse(`"type" must be one of: ${TOKEN_TYPES.join(", ")}.`, "invalid_params");
	}

	return {
		key: text(sent.key, "key"),
		token_name: text(sent.token_name, "token_name"),
		type,
		value: text(sent.value, "value"),
		dark_value: sent.dark_value ?? null,
		group: sent.group ?? null,
	};
};

/**
 * Upserts by `key`, and never deletes what the call leaves unmentioned. Dropping
 * from ten shades to six needs an explicit `unset` for the four that fell out.
 */
const set = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params).tokens;
	if (!Array.isArray(sent) || !sent.length) {
		throw refuse("\"tokens\" must be a non-empty list.", "invalid_params");
	}

	return invoke("builder.extensions.tokens.set_extension_tokens", {
		extension: extension.name,
		tokens: sent.map(readToken),
	}).then(async (result) => {
		await builderTokens.reload();
		return result;
	});
};

const unset = (params: unknown, extension: InstalledExtension) => {
	return invoke("builder.extensions.tokens.unset_extension_token", {
		extension: extension.name,
		key: text(fields(params).key, "key"),
	}).then(async (result) => {
		await builderTokens.reload();
		return result;
	});
};

export const tokenMethods: MethodTable = {
	// a network call, not a client write, so read-only refuses it in the bridge too
	"tokens.set": { needs: "token.write", run: set },
	"tokens.unset": { needs: "token.write", run: unset },
};
