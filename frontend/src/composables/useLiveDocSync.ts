import { onMounted, onUnmounted, watch } from "vue";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { builderSettings } from "@/data/builderSettings";
import type { BuilderPage } from "@/types/doctypes";

interface DocUpdatePayload {
	doctype: string;
	name: string;
}

export function useBuilderSettingsSync() {
	const builderStore = useBuilderStore();
	const { realtime } = builderStore;

	const handler = (data: DocUpdatePayload) => {
		if (data.doctype !== "Builder Settings") return;
		builderSettings.reload();
	};

	onMounted(() => {
		realtime.doc_subscribe("Builder Settings", "Builder Settings");
		realtime.on("doc_update", handler);
	});

	onUnmounted(() => {
		realtime.doc_unsubscribe("Builder Settings", "Builder Settings");
		realtime.off("doc_update", handler);
	});
}

export function useActivePageSync() {
	const builderStore = useBuilderStore();
	const pageStore = usePageStore();
	const { realtime } = builderStore;

	const handler = async (data: DocUpdatePayload) => {
		if (data.doctype !== "Builder Page") return;
		const activeName = pageStore.activePage?.name;
		if (!activeName || data.name !== activeName) return;

		if (pageStore.savingPage) return;
		const fresh = await pageStore.fetchActivePage(activeName);

		if (!fresh || pageStore.savingPage || pageStore.activePage?.name !== activeName) return;

		const { draft_blocks: freshDraftBlocks, blocks: _blocks, ...meta } = fresh as BuilderPage;
		Object.assign(pageStore.activePage, meta);

		if (freshDraftBlocks) {
			try {
				const freshBlocks = JSON.parse(freshDraftBlocks as string);
				const scriptMap = new Map<string, { blockClientScript?: string; blockDataScript?: string }>();

				function collectScripts(
					blocks: {
						blockId: string;
						blockClientScript?: string;
						blockDataScript?: string;
						children?: any[];
					}[],
				) {
					for (const b of blocks) {
						scriptMap.set(b.blockId, {
							blockClientScript: b.blockClientScript,
							blockDataScript: b.blockDataScript,
						});
						if (b.children?.length) collectScripts(b.children);
					}
				}
				collectScripts(freshBlocks);

				function applyScripts(
					blocks: {
						blockId: string;
						blockClientScript?: string;
						blockDataScript?: string;
						children?: any[];
					}[],
				) {
					for (const block of blocks) {
						const scripts = scriptMap.get(block.blockId);
						if (scripts) {
							if (scripts.blockClientScript !== undefined)
								block.blockClientScript = scripts.blockClientScript;
							if (scripts.blockDataScript !== undefined) block.blockDataScript = scripts.blockDataScript;
						}
						if (block.children?.length) applyScripts(block.children);
					}
				}
				applyScripts(pageStore.pageBlocks);
			} catch {
				// ignore JSON parse errors
			}
		}
	};

	realtime.on("doc_update", handler);

	watch([() => pageStore.activePage, () => realtime.subscribing], () => {
		if (realtime.subscribing) {
			return;
		}
		realtime.doc_subscribe("Builder Page", pageStore.activePage?.name as string);
	});

	onUnmounted(() => {
		realtime.doc_unsubscribe("Builder Page", pageStore.activePage?.name as string);
		realtime.off("doc_update", handler);
	});
}
