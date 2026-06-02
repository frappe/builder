import { type Ref, watch, toRaw, onUnmounted } from "vue";
import useBuilderStore from "@/stores/builderStore";
import { call } from "frappe-ui";
import { useExternalEditor } from "./useExternalEditor";
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
	const { realtime } = useBuilderStore();
	const { isExternalEditorActive } = useExternalEditor();

	watch(
		[() => context.value, () => isExternalEditorActive.value],
		([ctx]) => {
			if (!isExternalEditorActive.value || !hasValidContext(ctx)) return;

			const key = `${ctx.doctype}:${ctx.docname}`;
			if (!realtime.open_docs.has(key)) {
				realtime.doc_subscribe(ctx.doctype, ctx.docname);
			}

			const handleDocUpdate = async (data: { doctype: string; name: string }) => {
				if (data.doctype !== ctx.doctype || data.name !== ctx.docname) return;

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

				if (newValue !== getCurrentValue()) onUpdate(newValue);
			};

			realtime.on("doc_update", handleDocUpdate);
		},
		{ immediate: true },
	);

	onUnmounted(() => {
		const ctx = context.value;
		if (!isExternalEditorActive.value || !hasValidContext(ctx)) return;
		const key = `${ctx.doctype}:${ctx.docname}`;
		if (realtime.open_docs.has(key)) {
			realtime.doc_unsubscribe(ctx.doctype, ctx.docname);
		}
	});
}
