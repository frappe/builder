<template>
	<div v-show="isSmallScreen" class="grid h-screen w-screen place-content-center gap-4 text-ink-gray-9">
		<img src="/builder_logo.png" alt="logo" class="h-10" />
		<div class="flex flex-col">
			<h1 class="text-p-2xl font-semibold">Screen too small</h1>
			<p class="text-p-base">Please switch to a larger screen to edit</p>
		</div>
	</div>
	<div v-show="!isSmallScreen" class="page-builder h-screen flex-col overflow-hidden bg-surface-gray-1">
		<BlockContextMenu ref="blockContextMenu"></BlockContextMenu>
		<BuilderToolbar class="relative z-30"></BuilderToolbar>
		<div>
			<BuilderLeftPanel
				v-show="store.showLeftPanel"
				class="absolute bottom-0 left-0 top-[var(--toolbar-height)] z-[21] border-r-[1px] border-outline-gray-2 bg-surface-white"></BuilderLeftPanel>
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
						class="absolute left-0 right-0 top-0 z-20 flex items-center justify-between bg-surface-white p-2 text-sm text-ink-gray-8 shadow-sm">
						<div class="flex items-center gap-1 pl-2 text-xs">
							<a @click="store.exitFragmentMode" class="cursor-pointer">Page</a>
							<FeatherIcon name="chevron-right" class="h-3 w-3" />
							<span class="flex items-center gap-2">
								{{ store.fragmentData.fragmentName }}
								<a @click="pageListDialog = true" class="cursor-pointer text-ink-gray-4 underline">
									{{ usageMessage }}
								</a>
							</span>
						</div>
						<BuilderButton variant="solid" class="text-xs" @click="saveAndExitFragmentMode">
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
			<PageListModal v-model="pageListDialog" :pages="componentUsedInPages"></PageListModal>
			<Dialog
				style="z-index: 40"
				v-model="store.showHTMLDialog"
				class="overscroll-none"
				:isDirty="htmlEditor?.isDirty"
				:options="{
					title: 'HTML',
					size: '6xl',
				}">
				<template #body-content>
					<CodeEditor
						:modelValue="store.editableBlock?.getInnerHTML()"
						ref="htmlEditor"
						type="HTML"
						height="60vh"
						label="Edit HTML"
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
import BlockContextMenu from "@/components/BlockContextMenu.vue";
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import BuilderLeftPanel from "@/components/BuilderLeftPanel.vue";
import BuilderRightPanel from "@/components/BuilderRightPanel.vue";
import BuilderToolbar from "@/components/BuilderToolbar.vue";
import Dialog from "@/components/Controls/Dialog.vue";
import PageListModal from "@/components/Modals/PageListModal.vue";
import { webPages } from "@/data/webPage";
import { sessionUser } from "@/router";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { getUsersInfo } from "@/usersInfo";
import blockController from "@/utils/blockController";
import { isTargetEditable } from "@/utils/helpers";
import { useBuilderEvents } from "@/utils/useBuilderEvents";
import {
	breakpointsTailwind,
	useActiveElement,
	useBreakpoints,
	useDebounceFn,
	useMagicKeys,
} from "@vueuse/core";
import { createResource } from "frappe-ui";
import { computed, onActivated, onDeactivated, provide, ref, toRef, watch, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";
import CodeEditor from "../components/Controls/CodeEditor.vue";

const htmlEditor = ref<null | InstanceType<typeof CodeEditor>>(null);

const breakpoints = useBreakpoints(breakpointsTailwind);
const isSmallScreen = breakpoints.smaller("lg");

const route = useRoute();
const router = useRouter();
const store = useStore();
const usageCount = ref(0);
const componentUsedInPages = ref<BuilderPage[]>([]);
const pageListDialog = ref(false);

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

const blockContextMenu = toRef(store, "blockContextMenu");

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

async function saveAndExitFragmentMode(e: Event) {
	await store.fragmentData.saveAction?.(fragmentCanvas.value?.getRootBlock());
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

const usageMessage = computed(() => {
	if (usageCount.value === 0) {
		return "not used in any pages";
	}
	if (usageCount.value === 1) {
		return "used in 1 page";
	}
	return `used in ${usageCount.value} pages`;
});

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

watch(
	() => fragmentCanvas.value,
	(value) => {
		if (value) {
			const usageCountResource = createResource({
				method: "POST",
				url: "builder.builder.doctype.builder_settings.builder_settings.get_component_usage_count",
				params: {
					component_id: store.fragmentData.fragmentId,
				},
				auto: true,
			});
			usageCountResource.promise.then((res: { count: number; pages: BuilderPage[] }) => {
				usageCount.value = res.count;
				componentUsedInPages.value = res.pages;
			});
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
