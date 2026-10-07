/**
 * The design tokens that an extension makes while the editor runs.
 *
 * `block.update` changes the block tree in memory. A token must exist on the
 * server, because `Builder Token` gives the data for `/builder_assets/tokens.css`.
 * The **published** site serves that file, and an extension frame never runs there.
 *
 * So these calls resolve only when the Frappe method returns. A frame that
 * waits for one waits for a network round trip.
 *
 * The manifest has no field for a token list. A palette comes from a choice
 * that the user makes after the install. So no fixed list exists.
 */

import { createResource } from "frappe-ui";
import builderTokens from "@/data/builderToken";
import type { MethodTable } from "../bridge/permissions";
import { fields, refuse, text } from "../bridge/params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

const TOKEN_TYPES = ["Color", "Dimension", "Font"] as const;

/** One call, as `router.ts` and `usersInfo.ts` call a whitelisted method. */
const invoke = (url: string, params: Record<string, unknown>) => createResource({ url }).submit(params);

/**
 * `key` is the stable id that the extension gives. `Builder Token.name` is a
 * uuid from the database, and the extension never sees it. The other fields
 * are the fields of the doctype.
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
 * Adds or changes rows by `key`. It never removes a row that the call does not
 * name. To go from ten shades to six, call `unset` for the four old shades.
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
	// a network call, not a client write. The bridge also refuses it in read-only mode
	"tokens.set": { needs: "token.write", run: set },
	"tokens.unset": { needs: "token.write", run: unset },
};
