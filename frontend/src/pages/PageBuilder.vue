<template>
	<div v-show="isSmallScreen" class="grid h-screen w-screen place-content-center gap-4 text-ink-gray-9">
		<img src="/builder_logo.png" alt="logo" class="h-10" />
		<div class="flex flex-col">
			<h1 class="text-p-2xl font-semibold">Screen too small</h1>
			<p class="text-p-base">Please switch to a larger screen to edit</p>
		</div>
	</div>
	<div v-show="!isSmallScreen" class="page-builder relative h-screen overflow-hidden bg-surface-gray-1">
		<!-- Canvas layer (bottom) - comes first in DOM -->
		<BuilderCanvas
			ref="fragmentCanvas"
			:key="canvasStore.fragmentData.block?.blockId"
			v-if="canvasStore.editingMode === 'fragment' && canvasStore.fragmentData.block"
			:block-data="canvasStore.fragmentData.block"
			:canvas-styles="{
				width: (canvasStore.fragmentData.block.getStyle('width') + '').endsWith('px') ? '!fit-content' : null,
				padding: '40px',
			}"
			:style="{
				top: 'var(--toolbar-height)',
				left: `${
					builderStore.showLeftPanel
						? builderStore.builderLayout.leftPanelWidth + builderStore.builderLayout.optionsPanelWidth
						: 0
				}px`,
				right: `${builderStore.showRightPanel ? builderStore.builderLayout.rightPanelWidth : 0}px`,
			}"
			class="canvas-container absolute bottom-0 flex justify-center overflow-hidden bg-surface-gray-2 p-10">
			<template v-slot:header>
				<div class="flex items-center justify-between bg-surface-white p-2 text-sm text-ink-gray-8 shadow-sm">
					<div class="flex items-center gap-1 pl-2 text-xs">
						<a @click="canvasStore.exitFragmentMode" class="cursor-pointer">Page</a>
						<FeatherIcon name="chevron-right" class="h-3 w-3" />
						<span class="flex items-center gap-2">
							{{ canvasStore.fragmentData.fragmentName }}
							<a
								@click="pageListDialog = true"
								class="cursor-pointer text-ink-gray-4 underline"
								v-if="canvasStore.fragmentData.showUsageCount">
								{{ usageMessage }}
							</a>
						</span>
					</div>
					<BuilderButton variant="solid" class="text-xs" @click="saveAndExitFragmentMode">
						{{ canvasStore.fragmentData.saveActionLabel || "Save" }}
					</BuilderButton>
				</div>
			</template>
		</BuilderCanvas>
		<BuilderCanvas
			v-show="canvasStore.editingMode === 'page'"
			ref="pageCanvas"
			v-if="pageStore.pageBlocks[0]"
			:block-data="pageStore.pageBlocks[0]"
			:canvas-styles="{
				minHeight: '1000px',
			}"
			:style="{
				top: 'var(--toolbar-height)',
				left: `${
					builderStore.showLeftPanel
						? builderStore.builderLayout.leftPanelWidth + builderStore.builderLayout.optionsPanelWidth
						: 0
				}px`,
				right: `${builderStore.showRightPanel ? builderStore.builderLayout.rightPanelWidth : 0}px`,
			}"
			class="canvas-container absolute bottom-0 flex justify-center overflow-hidden bg-surface-gray-1 p-10"></BuilderCanvas>

		<!-- Panels layer (middle) - comes after canvas in DOM -->
		<BuilderLeftPanel
			v-show="builderStore.showLeftPanel"
			class="absolute bottom-0 left-0 top-[var(--toolbar-height)] w-fit border-r-[1px] border-outline-gray-2 bg-surface-white"></BuilderLeftPanel>
		<BuilderRightPanel
			v-show="builderStore.showRightPanel"
			class="no-scrollbar absolute bottom-0 right-0 top-[var(--toolbar-height)] overflow-auto border-l-[1px] border-outline-gray-2 bg-surface-white"></BuilderRightPanel>

		<!-- Toolbar layer (top) - comes last in DOM -->
		<BuilderToolbar class="absolute left-0 right-0 top-0"></BuilderToolbar>
	</div>
	<PageListModal v-model="pageListDialog" :pages="componentUsedInPages"></PageListModal>
	<Dialog
		v-model="canvasStore.showEditorDialog"
		class="overscroll-none"
		:isDirty="expandedEditor?.isDirty"
		:options="{
			title: 'HTML',
			size: '7xl',
		}">
		<template #body-content>
			<CodeEditor
				:modelValue="getExpandedEditorContent()"
				ref="expandedEditor"
				:type="expandedEditorOptions.type"
				height="68vh"
				:label="expandedEditorOptions.label"
				:showLineNumbers="true"
				:showSaveButton="true"
				@save="saveExpandedEditorContent"
				required />
		</template>
	</Dialog>
	<AIPageGeneratorModal
		v-model="showAIGeneratorDialog"
		:pageId="route.params.pageId as string"
		:mode="aiMode"
		:blockContext="modifyBlockContext"
		@generated="handleGeneratedBlocks"
		@streaming="handleStreamingBlocks"
		@modified="handleModifiedBlocks"
		@modifyStreaming="handleModifyStreamingBlocks"
		@generating="isAIGenerating = $event"
		ref="aiGeneratorModal"></AIPageGeneratorModal>
	<BlockContextMenu ref="blockContextMenu"></BlockContextMenu>
	<KeyboardShortcutsModal ref="shortcutsModal" />
</template>

<script setup lang="ts">
import type Block from "@/block";
import AIPageGeneratorModal from "@/components/AIPageGeneratorModal.vue";
import BlockContextMenu from "@/components/BlockContextMenu.vue";
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import BuilderLeftPanel from "@/components/BuilderLeftPanel.vue";
import BuilderRightPanel from "@/components/BuilderRightPanel.vue";
import BuilderToolbar from "@/components/BuilderToolbar.vue";
import Dialog from "@/components/Controls/Dialog.vue";
import KeyboardShortcutsModal from "@/components/KeyboardShortcutsModal.vue";
import PageListModal from "@/components/Modals/PageListModal.vue";
import { webPages } from "@/data/webPage";
import { sessionUser } from "@/router";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { getUsersInfo } from "@/usersInfo";
import blockController from "@/utils/blockController";
import { getBlockInstance, getBlockObject, getRootBlockTemplate } from "@/utils/helpers";
import { useBuilderEvents } from "@/utils/useBuilderEvents";
import { useShortcut } from "@/utils/useShortcut";
import { breakpointsTailwind, useBreakpoints, useDebounceFn, useEventListener } from "@vueuse/core";
import { createResource } from "frappe-ui";
import { computed, onActivated, onDeactivated, onMounted, provide, ref, watch, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";
import CodeEditor from "../components/Controls/CodeEditor.vue";

const expandedEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const aiGeneratorModal = ref<null | InstanceType<typeof AIPageGeneratorModal>>(null);

const breakpoints = useBreakpoints(breakpointsTailwind);
const isSmallScreen = breakpoints.smaller("lg");

const route = useRoute();
const router = useRouter();
const builderStore = useBuilderStore();
const pageStore = usePageStore();
const canvasStore = useCanvasStore();
const usageCount = ref(0);
const componentUsedInPages = ref<BuilderPage[]>([]);
const pageListDialog = ref(false);
const blockContextMenu = ref<InstanceType<typeof BlockContextMenu> | null>(null);
const showAIGeneratorDialog = ref(false);
const aiMode = ref<"generate" | "modify">("generate");
const modifyBlockContext = ref<Record<string, any> | null>(null);
const modifyBlockId = ref<string | null>(null);
const isAIGenerating = ref(false);

provide("showAIGenerator", () => {
	aiMode.value = "generate";
	modifyBlockContext.value = null;
	modifyBlockId.value = null;
	showAIGeneratorDialog.value = true;
});

const editWithAIFn = (block: Block) => {
	aiMode.value = "modify";
	modifyBlockContext.value = getBlockObject(block);
	modifyBlockId.value = block.blockId;
	showAIGeneratorDialog.value = true;
};
provide("editWithAI", editWithAIFn);

const runDirectAI = (block: Block, type: "rewrite_text" | "replace_image", customPrompt?: string) => {
	const blockObj = getBlockObject(block);
	aiMode.value = "modify";
	modifyBlockId.value = block.blockId;
	modifyBlockContext.value = blockObj;
	aiGeneratorModal.value?.executeDirect(blockObj, type, customPrompt);
};
provide("runDirectAI", runDirectAI);

const handleGeneratedBlocks = () => {
	pageStore.savePage();
};

const handleStreamingBlocks = (block: Block) => {
	if (!block) return;

	try {
		pageStore.pageBlocks = [getBlockInstance(block)];
		canvasStore.activeCanvas?.setRootBlock(pageStore.pageBlocks[0] as Block, false);
	} catch {
		// Partial block may still be invalid, skip this frame
	}
};

const replaceBlockInTree = (root: Block, targetId: string, replacement: BlockOptions): boolean => {
	if (!root || !replacement) return false;
	if (root.blockId === targetId) {
		root.element = replacement.element || root.element;
		root.baseStyles = replacement.baseStyles || root.baseStyles;
		root.mobileStyles = replacement.mobileStyles || root.mobileStyles;
		root.tabletStyles = replacement.tabletStyles || root.tabletStyles;
		root.classes = replacement.classes || root.classes;

		if (replacement.attributes) {
			root.attributes = { ...root.attributes, ...replacement.attributes };
		}

		if (replacement.innerText !== undefined) root.innerText = replacement.innerText;
		if (replacement.innerHTML !== undefined) root.innerHTML = replacement.innerHTML;

		if (replacement.children) {
			root.children.splice(
				0,
				root.children.length,
				...replacement.children.map((child) => getBlockInstance(child)),
			);
		}
		return true;
	}
	return root.children?.some((child: Block) => replaceBlockInTree(child, targetId, replacement)) || false;
};

const handleModifiedBlocks = () => {
	pageStore.savePage();
	modifyBlockContext.value = null;
	modifyBlockId.value = null;
	aiMode.value = "generate";
};

const handleModifyStreamingBlocks = (block: BlockOptions) => {
	const targetId = block?.blockId || modifyBlockId.value;
	if (!block || !targetId) return;

	try {
		const rootBlock = pageStore.pageBlocks[0] as Block;
		if (rootBlock) {
			replaceBlockInTree(rootBlock, targetId, block);
		}
	} catch {
		// Partial block may still be invalid, skip this frame
	}
};

watch([() => canvasStore.editableBlock, () => pageStore.activePage?.is_standard], () => {
	builderStore.toggleReadOnlyMode(
		canvasStore.editingMode === "page" &&
			Boolean(pageStore.activePage?.is_standard) &&
			!window.is_developer_mode,
	);
});

declare global {
	interface Window {
		blockController: typeof blockController;
	}
}

window.blockController = blockController;

const pageCanvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);
const fragmentCanvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);

provide("pageCanvas", pageCanvas);
provide("fragmentCanvas", fragmentCanvas);
useBuilderEvents(pageCanvas, fragmentCanvas, saveAndExitFragmentMode, route, router);

const shortcutsModal = ref<InstanceType<typeof KeyboardShortcutsModal> | null>(null);

provide("showShortcuts", () => {
	if (shortcutsModal.value) {
		shortcutsModal.value.showDialog = true;
	}
});

useShortcut([
	{
		key: " ",
		description: "Hold for move mode",
		group: "Tools",
		handler: () => {
			if (!canvasStore.editableBlock) {
				builderStore.mode = "move";
			}
		},
		preventDefault: true,
	},
	{
		key: "?",
		description: "Show keyboard shortcuts",
		group: "General",
		handler: () => {
			if (shortcutsModal.value) {
				shortcutsModal.value.showDialog = true;
			}
		},
	},
	{
		key: "i",
		ctrl: true,
		description: "Edit block with AI",
		group: "Block",
		condition: () =>
			!blockController.isRoot() && !blockController.multipleBlocksSelected() && !builderStore.readOnlyMode,
		handler: () => {
			const block = blockController.getSelectedBlocks()[0];
			if (block) {
				editWithAIFn?.(block);
			}
		},
	},
]);

// When space is released, revert back to last mode
useEventListener(document, "keyup", (e) => {
	if (e.key === " " && builderStore.mode === "move") {
		builderStore.mode = builderStore.lastMode !== "move" ? builderStore.lastMode : "select";
	}
});

async function saveAndExitFragmentMode(e: Event) {
	await canvasStore.fragmentData.saveAction?.(fragmentCanvas.value?.getRootBlock());
	fragmentCanvas.value?.toggleDirty(false);
	canvasStore.exitFragmentMode(e);
}

let expandedEditorOptions = computed(() => {
	let title, label;
	let type: "HTML" | "JavaScript" | "CSS" | "Python" = "HTML";
	if (canvasStore.editingContentType === "html") {
		title = "HTML";
		label = "Edit HTML";
	} else if (canvasStore.editingContentType === "js") {
		title = "Block Client Script";
		label = "Edit Block Client Script";
		type = "JavaScript";
	} else if (canvasStore.editingContentType === "css") {
		title = "CSS";
		label = "Edit CSS";
		type = "CSS";
	} else if (canvasStore.editingContentType === "python") {
		title = "Block Data Script";
		label = "Edit Block Data Script";
		type = "Python";
	}
	return { title, label, type };
});

function getExpandedEditorContent() {
	if (canvasStore.editingContentType === "html") {
		return canvasStore.editableBlock?.getInnerHTML();
	} else if (canvasStore.editingContentType === "js") {
		return canvasStore.editableBlock?.getBlockClientScript();
	} else if (canvasStore.editingContentType === "python") {
		return canvasStore.editableBlock?.getBlockDataScript();
	}
}

async function saveExpandedEditorContent(val: string) {
	if (canvasStore.editingContentType === "html") {
		canvasStore.editableBlock?.setInnerHTML(val);
	} else if (canvasStore.editingContentType === "js") {
		canvasStore.editableBlock?.setBlockClientScript(val);
	} else if (canvasStore.editingContentType === "python") {
		canvasStore.editableBlock?.setBlockDataScript(val);
	}
	canvasStore.showEditorDialog = false;
}

onActivated(async () => {
	builderStore.realtime.on("doc_viewers", async (data: { users: [] }) => {
		builderStore.viewers = await getUsersInfo(
			data.users.filter((user: string) => user !== sessionUser.value),
		);
	});
	builderStore.realtime.doc_subscribe("Builder Page", route.params.pageId as string);
	builderStore.realtime.doc_open("Builder Page", route.params.pageId as string);
	if (route.params.pageId === pageStore.selectedPage) {
		return;
	}
	if (!webPages.data) {
		await webPages.fetchOne.submit(route.params.pageId as string);
	}
	if (route.params.pageId && route.params.pageId !== "new") {
		pageStore.setPage(route.params.pageId as string, true, route.query);
	}
});

watch(
	route,
	(to, from) => {
		if (to.name === "builder" && to.params.pageId === "new") {
			const pageInfo = {
				page_title: "My Page",
				draft_blocks: [getRootBlockTemplate()],
			} as BuilderPage;
			if (builderStore.activeFolder) {
				pageInfo["project_folder"] = builderStore.activeFolder;
			}
			webPages.insert.submit(pageInfo).then((data: BuilderPage) => {
				router.push({ name: "builder", params: { pageId: data.name }, force: true });
				pageStore.setPage(data.name);
			});
		}
	},
	{ immediate: true },
);

onDeactivated(() => {
	builderStore.realtime.doc_close("Builder Page", pageStore.activePage?.name as string);
	builderStore.realtime.off("doc_viewers", () => {});
	builderStore.viewers = [];
});

onMounted(() => {
	builderStore.blockContextMenu = blockContextMenu.value;
});

watchEffect(() => {
	if (fragmentCanvas.value) {
		canvasStore.activeCanvas = fragmentCanvas.value;
	} else {
		canvasStore.activeCanvas = pageCanvas.value;
	}
});

const debouncedPageSave = useDebounceFn(pageStore.savePage, 300);

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
			pageStore.selectedPage &&
			!pageStore.settingPage &&
			canvasStore.editingMode === "page" &&
			!pageCanvas.value?.canvasProps?.settingCanvas &&
			!isAIGenerating.value
		) {
			pageStore.savingPage = true;
			debouncedPageSave();
		}
	},
	{
		deep: true,
	},
);

watch(
	() => canvasStore.showEditorDialog,
	(value) => {
		if (!value) {
			canvasStore.editableBlock = null;
		}
	},
);

watch(
	() => fragmentCanvas.value,
	(value) => {
		if (value && canvasStore.fragmentData.fragmentId && canvasStore.fragmentData.showUsageCount) {
			const usageCountResource = createResource({
				method: "POST",
				url: "builder.builder.doctype.builder_settings.builder_settings.get_component_usage_count",
				params: {
					component_id: canvasStore.fragmentData.fragmentId,
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
	--toolbar-height: 3rem;
}
</style>
