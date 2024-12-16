<template>
	<div class="page-builder h-screen flex-col overflow-hidden bg-surface-gray-1">
		<BuilderToolbar class="relative z-30"></BuilderToolbar>
		<div>
			<BuilderLeftPanel
				v-show="store.showLeftPanel"
				class="absolute bottom-0 left-0 top-[var(--toolbar-height)] z-20 border-r-[1px] border-outline-gray-2 bg-surface-white"></BuilderLeftPanel>
			<BuilderCanvas
				ref="fragmentCanvas"
				:key="store.fragmentData.block?.blockId"
				v-if="store.editingMode === 'fragment' && store.fragmentData.block"
				:block-data="store.fragmentData.block"
				:canvas-styles="{
					width: (store.fragmentData.block.getStyle('width') + '').endsWith('px') ? '!fit-content' : null,
					padding: '40px',
				}"
				:style="{
					left: `${
						store.showLeftPanel
							? store.builderLayout.leftPanelWidth + store.builderLayout.optionsPanelWidth
							: 0
					}px`,
					right: `${store.showRightPanel ? store.builderLayout.rightPanelWidth : 0}px`,
				}"
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-surface-gray-2 p-10">
				<template v-slot:header>
					<div
						class="absolute left-0 right-0 top-0 z-20 flex items-center justify-between bg-surface-white p-2 text-sm text-gray-800 dark:text-zinc-400">
						<div class="flex items-center gap-1 text-xs">
							<a @click="store.exitFragmentMode" class="cursor-pointer">Page</a>
							<FeatherIcon name="chevron-right" class="h-3 w-3" />
							{{ store.fragmentData.fragmentName }}
						</div>
						<BuilderButton
							class="text-xs dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
							@click="saveAndExitFragmentMode">
							{{ store.fragmentData.saveActionLabel || "Save" }}
						</BuilderButton>
					</div>
				</template>
			</BuilderCanvas>
			<BuilderCanvas
				v-show="store.editingMode === 'page'"
				ref="pageCanvas"
				v-if="store.pageBlocks[0]"
				:block-data="store.pageBlocks[0]"
				:canvas-styles="{
					minHeight: '1000px',
				}"
				:style="{
					left: `${
						store.showLeftPanel
							? store.builderLayout.leftPanelWidth + store.builderLayout.optionsPanelWidth
							: 0
					}px`,
					right: `${store.showRightPanel ? store.builderLayout.rightPanelWidth : 0}px`,
				}"
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-surface-gray-1 p-10"></BuilderCanvas>
			<BuilderRightPanel
				v-show="store.showRightPanel"
				class="no-scrollbar absolute bottom-0 right-0 top-[var(--toolbar-height)] z-20 overflow-auto border-l-[1px] border-outline-gray-2 bg-surface-white"></BuilderRightPanel>
			<Dialog
				style="z-index: 40"
				v-model="store.showHTMLDialog"
				class="overscroll-none"
				:options="{
					title: 'HTML Code',
					size: '6xl',
				}">
				<template #body-content>
					<CodeEditor
						:modelValue="store.editableBlock?.getInnerHTML()"
						type="HTML"
						height="60vh"
						:showLineNumbers="true"
						:showSaveButton="true"
						@save="
							(val) => {
								store.editableBlock?.setInnerHTML(val);
								store.showHTMLDialog = false;
							}
						"
						required />
				</template>
			</Dialog>
		</div>
	</div>
</template>

<script setup lang="ts">
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import BuilderLeftPanel from "@/components/BuilderLeftPanel.vue";
import BuilderRightPanel from "@/components/BuilderRightPanel.vue";
import BuilderToolbar from "@/components/BuilderToolbar.vue";
import { webPages } from "@/data/webPage";
import { sessionUser } from "@/router";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { getUsersInfo } from "@/usersInfo";
import blockController from "@/utils/blockController";
import { isTargetEditable } from "@/utils/helpers";
import { useBuilderEvents } from "@/utils/useBuilderEvents";
import { useActiveElement, useDebounceFn, useMagicKeys } from "@vueuse/core";
import { Dialog } from "frappe-ui";
import { computed, onActivated, onDeactivated, provide, ref, watch, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";
import CodeEditor from "../components/Controls/CodeEditor.vue";

const route = useRoute();
const router = useRouter();
const store = useStore();

declare global {
	interface Window {
		store: typeof store;
		blockController: typeof blockController;
	}
}

window.store = store;
window.blockController = blockController;

const pageCanvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);
const fragmentCanvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);

provide("pageCanvas", pageCanvas);
provide("fragmentCanvas", fragmentCanvas);
useBuilderEvents(pageCanvas, fragmentCanvas, saveAndExitFragmentMode, route, router);

const activeElement = useActiveElement();
const notUsingInput = computed(
	() => activeElement.value?.tagName !== "INPUT" && activeElement.value?.tagName !== "TEXTAREA",
);

const { space } = useMagicKeys({
	passive: false,
	onEventFired(e) {
		if (e.key === " " && notUsingInput.value && !isTargetEditable(e)) {
			e.preventDefault();
		}
	},
});

watch(space, (value) => {
	if (value && !store.editableBlock) {
		store.mode = "move";
	} else if (store.mode === "move") {
		store.mode = store.lastMode !== "move" ? store.lastMode : "select";
	}
});

function saveAndExitFragmentMode(e: Event) {
	store.fragmentData.saveAction?.(fragmentCanvas.value?.getRootBlock());
	fragmentCanvas.value?.toggleDirty(false);
	store.exitFragmentMode(e);
}

onActivated(async () => {
	store.realtime.on("doc_viewers", async (data: { users: [] }) => {
		store.viewers = await getUsersInfo(data.users.filter((user: string) => user !== sessionUser.value));
	});
	store.realtime.doc_subscribe("Builder Page", route.params.pageId as string);
	store.realtime.doc_open("Builder Page", route.params.pageId as string);
	if (route.params.pageId === store.selectedPage) {
		return;
	}
	if (!webPages.data) {
		await webPages.fetchOne.submit(route.params.pageId as string);
	}
	if (route.params.pageId && route.params.pageId !== "new") {
		store.setPage(route.params.pageId as string);
	}
});

watch(
	route,
	(to, from) => {
		if (to.name === "builder" && to.params.pageId === "new") {
			const pageInfo = {
				page_title: "My Page",
				draft_blocks: [store.getRootBlockTemplate()],
			} as BuilderPage;
			if (store.activeFolder) {
				pageInfo["project_folder"] = store.activeFolder;
			}
			webPages.insert.submit(pageInfo).then((data: BuilderPage) => {
				router.push({ name: "builder", params: { pageId: data.name }, force: true });
				store.setPage(data.name);
			});
		}
	},
	{ immediate: true },
);

onDeactivated(() => {
	store.realtime.doc_close("Builder Page", store.activePage?.name as string);
	store.realtime.off("doc_viewers", () => {});
	store.viewers = [];
});

watchEffect(() => {
	if (fragmentCanvas.value) {
		store.activeCanvas = fragmentCanvas.value;
	} else {
		store.activeCanvas = pageCanvas.value;
	}
});

const debouncedPageSave = useDebounceFn(store.savePage, 300);

watch(
	() => pageCanvas.value?.block,
	() => {
		if (
			store.selectedPage &&
			!store.settingPage &&
			store.editingMode === "page" &&
			!pageCanvas.value?.canvasProps?.settingCanvas
		) {
			store.savingPage = true;
			debouncedPageSave();
		}
	},
	{
		deep: true,
	},
);

watch(
	() => store.showHTMLDialog,
	(value) => {
		if (!value) {
			store.editableBlock = null;
		}
	},
);
</script>

<style>
.page-builder {
	--left-panel-width: 17rem;
	--right-panel-width: 20rem;
	--toolbar-height: 3rem;
}
</style>
