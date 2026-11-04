import type { ChatMessage } from "./types";

/** HTML attributes that map to first-class Block attributes (vs. customAttributes). */
export const STANDARD_ATTRS = new Set([
	"src",
	"darkSrc",
	"alt",
	"href",
	"title",
	"value",
	"type",
	"placeholder",
]);

export function buildLocalMessage(
	role: "user" | "assistant",
	content: string,
	metadata: Record<string, any> = {},
): ChatMessage {
	return {
		id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		role,
		content,
		created_at: new Date().toISOString(),
		metadata,
	} as ChatMessage;
}

/** Models habitually write 'item.image' / 'data.merch_items', but the renderer
 * resolves binding keys RELATIVE to their context (the loop record inside a
 * repeater, the page-data root elsewhere) — those prefixes silently break
 * resolution. Normalize at the single point keys land. Mirrors
 * page_writer.strip_binding_prefix. */
export function stripBindingPrefix(key: unknown): string {
	const k = String(key ?? "").trim();
	for (const prefix of ["data.", "item.", "row."]) {
		if (k.startsWith(prefix)) return k.slice(prefix.length);
	}
	return k;
}

/** One binding entry from an edit's `bind` pair — the TS twin of
 * page_writer.binding_entry. 'props.<name>' / 'component.<key>' select the
 * source (comesFrom); anything else resolves against page data. */
export function bindingEntry(property: string, field: string | null | undefined): BlockDataKey {
	let key = String(field ?? "").trim();
	let comesFrom: BlockDataKey["comesFrom"];
	if (key.startsWith("props.")) {
		key = key.slice("props.".length);
		comesFrom = "props";
	} else if (key.startsWith("component.")) {
		key = key.slice("component.".length);
		comesFrom = "componentData";
	} else {
		key = stripBindingPrefix(key);
	}
	const isContent = property === "innerHTML" || property === "text";
	return {
		key,
		property: isContent ? "innerHTML" : property,
		type: (isContent ? "key" : "attribute") as BlockDataKeyType,
		...(comesFrom ? { comesFrom } : {}),
	};
}

/** A `bind.visible` key → the block's visibilityCondition, the TS twin of
 * page_writer.visibility_condition. */
export function visibilityCondition(field: string): BlockVisibilityCondition {
	const { key, comesFrom } = bindingEntry("visible", field);
	return { key, comesFrom: comesFrom ?? "dataScript" };
}
