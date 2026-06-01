import { type Ref, watchEffect } from "vue";
import useBuilderStore from "@/stores/builderStore";
import { call } from "frappe-ui";
import type { OpenScriptRequest } from "./useExternalEditor";

function findBlockById(blocks: Record<string, any>[], blockId: string): Record<string, any> | null {
	for (const block of blocks) {
		if (block.blockId === blockId) return block;
		if (block.children?.length) {
			const found = findBlockById(block.children, blockId);
			if (found) return found;
		}
	}
	return null;
}

function hasValidContext(ctx: OpenScriptRequest | undefined): ctx is OpenScriptRequest {
	if (!ctx) return false;
	return !!(ctx.field || (ctx.blockId && ctx.blockField));
}

export function useRealtimeDocSync(
	context: Ref<OpenScriptRequest | undefined>,
	getCurrentValue: () => string,
	onUpdate: (value: string) => void,
) {
	const builderStore = useBuilderStore();

	watchEffect((onCleanup) => {
		const ctx = context.value;
		if (!hasValidContext(ctx)) return;

		let isActive = true;

		const key = `${ctx.doctype}:${ctx.docname}`;
		const didSubscribe = !builderStore.realtime.open_docs.has(key);
		if (didSubscribe) {
			builderStore.realtime.doc_subscribe(ctx.doctype, ctx.docname);
		}

		const handleDocUpdate = async (data: { doctype: string; name: string }) => {
			if (!isActive || data.doctype !== ctx.doctype || data.name !== ctx.docname) return;

			let newValue: string;

			try {
				if (ctx.field) {
					const result = await call("frappe.client.get_value", {
						doctype: ctx.doctype,
						filters: ctx.docname,
						fieldname: ctx.field,
					});
					newValue = result?.[ctx.field] ?? "";
				} else {
					const result = await call("frappe.client.get_value", {
						doctype: ctx.doctype,
						filters: ctx.docname,
						fieldname: ["draft_blocks", "blocks"],
					});
					const blocksJson = result?.draft_blocks ?? result?.blocks ?? "[]";
					const blocks: Record<string, any>[] = JSON.parse(blocksJson);
					const block = findBlockById(Array.isArray(blocks) ? blocks : [blocks], ctx.blockId!);
					newValue = block?.[ctx.blockField!] ?? "";
				}
			} catch {
				return;
			}

			if (newValue === getCurrentValue()) return;

			onUpdate(newValue);
		};

		builderStore.realtime.on("doc_update", handleDocUpdate);

		onCleanup(() => {
			isActive = false;
			builderStore.realtime.off("doc_update", handleDocUpdate);
			if (didSubscribe) {
				builderStore.realtime.doc_unsubscribe(ctx.doctype, ctx.docname);
			}
		});
	});
}
