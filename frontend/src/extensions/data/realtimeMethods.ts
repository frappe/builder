/**
 * Forwards Frappe's realtime list updates to the extensions that watch a doctype.
 *
 * The host sees its own `data.*` writes, but not a write through `method.call`,
 * Desk, or another user. Frappe announces each of them as `list_update` to the
 * doctype's room, so the host joins that room and passes the update on.
 */

import useBuilderStore from "@/stores/builderStore";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import { fields, text } from "../bridge/params";

type ListUpdate = { doctype: string; name: string };

/** The doctypes that each extension watches. */
const watched = new Map<string, Set<string>>();

const forward = ({ doctype, name }: ListUpdate) =>
	watched.forEach((doctypes, extension) => {
		if (!doctypes.has(doctype)) return;
		// Frappe does not say which write it was
		const change = { doctype, name, operation: "change" };
		bridge.getChannels(extension).forEach((channel) => channel.emit("data.changed", change));
	});

const watch = (extension: string) => {
	if (!watched.size) useBuilderStore().realtime.on("list_update", forward);
	const doctypes = new Set<string>();
	watched.set(extension, doctypes);
	bridge.registerTeardown(extension, () => {
		watched.delete(extension);
		if (!watched.size) useBuilderStore().realtime.off("list_update", forward);
	});
	return doctypes;
};

/** Frappe joins the room only when this user can read the doctype. */
const subscribe = (params: unknown, extension: InstalledExtension) => {
	const doctype = text(fields(params).doctype, "doctype");
	const doctypes = watched.get(extension.name) ?? watch(extension.name);
	if (doctypes.has(doctype)) return;
	doctypes.add(doctype);
	// not `doctype_subscribe()`, which drops a second room within a second
	useBuilderStore().realtime.emit("doctype_subscribe", doctype);
};

export const realtimeMethods: MethodTable = {
	"data.subscribe": { needs: "data.access", run: subscribe },
};
