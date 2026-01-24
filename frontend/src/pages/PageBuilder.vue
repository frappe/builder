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
			:remote-users="remoteUsers"
			:is-collaboration-enabled="isCollaborationEnabled"
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
		<BuilderToolbar
			class="absolute left-0 right-0 top-0"
			:remote-users="remoteUsers"
			:following-user-id="followingUserId"
			@follow-user="handleFollowUser"></BuilderToolbar>
	</div>
	<PageListModal v-model="pageListDialog" :pages="componentUsedInPages"></PageListModal>
	<Dialog
		v-model="canvasStore.showHTMLDialog"
		class="overscroll-none"
		:isDirty="htmlEditor?.isDirty"
		:options="{
			title: 'HTML',
			size: '7xl',
		}">
		<template #body-content>
			<CodeEditor
				:modelValue="canvasStore.editableBlock?.getInnerHTML()"
				ref="htmlEditor"
				type="HTML"
				height="68vh"
				label="Edit HTML"
				:showLineNumbers="true"
				:showSaveButton="true"
				@save="
					(val) => {
						canvasStore.editableBlock?.setInnerHTML(val);
						canvasStore.showHTMLDialog = false;
					}
				"
				required />
		</template>
	</Dialog>
	<BlockContextMenu ref="blockContextMenu"></BlockContextMenu>
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
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { getUsersInfo } from "@/usersInfo";
import blockController from "@/utils/blockController";
import { getBlockInstance, getBlockString, getRootBlockTemplate, isTargetEditable } from "@/utils/helpers";
import { useBuilderEvents } from "@/utils/useBuilderEvents";
import { useYjsCollaboration } from "@/utils/useYjsCollaboration";
import { UserAwareness } from "@/utils/yjsHelpers";
import {
	breakpointsTailwind,
	useActiveElement,
	useBreakpoints,
	useDebounceFn,
	useMagicKeys,
} from "@vueuse/core";
import { createResource } from "frappe-ui";
import { computed, onActivated, onDeactivated, onMounted, provide, ref, watch, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";
import CodeEditor from "../components/Controls/CodeEditor.vue";

const htmlEditor = ref<null | InstanceType<typeof CodeEditor>>(null);

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

// Yjs Collaborative Editing
const yjsCollaboration = ref<ReturnType<typeof useYjsCollaboration> | null>(null);
const remoteUsers = ref<Map<number, UserAwareness>>(new Map());
const isCollaborationEnabled = ref(false);
const isRemoteUpdate = ref(false);
const followingUserId = ref<number | null>(null);

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
provide("remoteUsers", remoteUsers);
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
	if (value && !canvasStore.editableBlock) {
		builderStore.mode = "move";
	} else if (builderStore.mode === "move") {
		builderStore.mode = builderStore.lastMode !== "move" ? builderStore.lastMode : "select";
	}
});

// Track mouse movement for collaborative cursors
const debouncedCursorUpdate = useDebounceFn((e: MouseEvent) => {
	if (isCollaborationEnabled.value && yjsCollaboration.value && pageCanvas.value) {
		// Stop following when user moves their cursor
		// if (followingUserId.value !== null) {
		// 	followingUserId.value = null;
		// }

		// Get the actual canvas element (the one with fixed width, e.g., 1400px)
		const canvasElement = document.querySelector(".canvas:not([style*='display: none'])") as HTMLElement;

		if (canvasElement) {
			// Get the canvas element's bounding rect (already accounts for parent transforms)
			const canvasRect = canvasElement.getBoundingClientRect();

			// Get the current scale from the page canvas
			const currentScale = pageCanvas.value?.canvasProps?.scale || 1;

			// Calculate position relative to the canvas element (visual coordinates)
			const visualX = e.clientX - canvasRect.left;
			const visualY = e.clientY - canvasRect.top;

			// Convert visual coordinates to logical coordinates (independent of scale)
			// This ensures cursors point to the same logical position regardless of zoom
			const logicalX = visualX / currentScale;
			const logicalY = visualY / currentScale;

			// Store logical canvas coordinates (same logical position for all users)
			yjsCollaboration.value.updateLocalCursor(null, {
				x: logicalX,
				y: logicalY,
			});
		}
	}
}, 16);

async function saveAndExitFragmentMode(e: Event) {
	await canvasStore.fragmentData.saveAction?.(fragmentCanvas.value?.getRootBlock());
	fragmentCanvas.value?.toggleDirty(false);
	canvasStore.exitFragmentMode(e);
}

// Handle following a user's cursor
function handleFollowUser(clientId: number) {
	if (followingUserId.value === clientId) {
		// Toggle off if clicking the same user
		followingUserId.value = null;
	} else {
		followingUserId.value = clientId;
	}
}

// Watch the followed user's cursor and pan canvas to keep it in viewport
watch(
	[remoteUsers, followingUserId],
	() => {
		if (followingUserId.value === null || !pageCanvas.value) return;

		const followedUser = remoteUsers.value.get(followingUserId.value);
		if (!followedUser?.cursor?.position) return;

		const canvasElement = document.querySelector(".canvas:not([style*='display: none'])") as HTMLElement;
		if (!canvasElement) return;

		const canvasRect = canvasElement.getBoundingClientRect();
		const currentScale = pageCanvas.value?.canvasProps?.scale || 1;

		// Get the followed user's cursor position (logical coordinates)
		const logicalX = followedUser.cursor.position.x;
		const logicalY = followedUser.cursor.position.y;

		// Convert to visual coordinates
		const visualX = logicalX * currentScale;
		const visualY = logicalY * currentScale;

		// Calculate cursor position in screen space
		const canvasScreenX = canvasRect.left + visualX;
		const canvasScreenY = canvasRect.top + visualY;

		// Define viewport bounds with padding to avoid edge placement
		const padding = 50; // pixels of padding from edges
		const viewportLeft =
			padding + builderStore.builderLayout.leftPanelWidth + builderStore.builderLayout.optionsPanelWidth;
		const viewportRight = window.innerWidth - padding - builderStore.builderLayout.rightPanelWidth;
		const viewportTop = padding;
		const viewportBottom = window.innerHeight - padding;

		// Check if cursor is outside viewport
		const isOutOfView =
			canvasScreenX < viewportLeft ||
			canvasScreenX > viewportRight ||
			canvasScreenY < viewportTop ||
			canvasScreenY > viewportBottom;

		// Only adjust canvas position if cursor is out of view
		if (isOutOfView && pageCanvas.value.canvasProps) {
			const currentTranslateX = pageCanvas.value.canvasProps.translateX || 0;
			const currentTranslateY = pageCanvas.value.canvasProps.translateY || 0;

			let deltaX = 0;
			let deltaY = 0;

			// Calculate minimal adjustment to bring cursor into view
			if (canvasScreenX < viewportLeft) {
				deltaX = (viewportLeft - canvasScreenX) / currentScale;
			} else if (canvasScreenX > viewportRight) {
				deltaX = (viewportRight - canvasScreenX) / currentScale;
			}

			if (canvasScreenY < viewportTop) {
				deltaY = (viewportTop - canvasScreenY) / currentScale;
			} else if (canvasScreenY > viewportBottom) {
				deltaY = (viewportBottom - canvasScreenY) / currentScale;
			}

			// Update canvas translate to bring cursor into view
			pageCanvas.value.canvasProps.translateX = currentTranslateX + deltaX;
			pageCanvas.value.canvasProps.translateY = currentTranslateY + deltaY;
		}
	},
	{ deep: true },
);

// Initialize Yjs collaborative editing
function initializeCollaboration(pageId: string) {
	if (!sessionUser.value || !pageId || pageId === "new") {
		return;
	}

	try {
		// Get user image from frappe boot if available
		const userImage = (window as any).frappe?.boot?.user_info?.[sessionUser.value]?.image;

		yjsCollaboration.value = useYjsCollaboration({
			documentName: `builder-page-${pageId}`,
			userId: sessionUser.value,
			userName: sessionUser.value.split("@")[0] || sessionUser.value,
			userImage: userImage || undefined,
			onRemoteUpdate: (data) => {
				// Handle remote updates from other users
				if (data.blocks && canvasStore.editingMode === "page") {
					isRemoteUpdate.value = true;
					try {
						const blockInstance = getBlockInstance(data.blocks);
						if (pageCanvas.value && blockInstance) {
							pageCanvas.value.setRootBlock(blockInstance);
						}
					} catch (error) {
						console.error("Error applying remote update:", error);
					} finally {
						setTimeout(() => {
							isRemoteUpdate.value = false;
						}, 100);
					}
				}
			},
			onAwarenessChange: (users) => {
				// Update remote users for cursor display
				remoteUsers.value = users;
			},
		});
		isCollaborationEnabled.value = true;
	} catch (error) {
		console.error("Failed to initialize Yjs collaboration:", error);
		isCollaborationEnabled.value = false;
	}
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
		// Initialize Yjs collaboration for the page
		initializeCollaboration(route.params.pageId as string);
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

onMounted(() => {
	builderStore.blockContextMenu = blockContextMenu.value;
	// Add mouse move listener for cursor tracking
	document.addEventListener("mousemove", debouncedCursorUpdate);
});

// Watch for canvas panning to update cursor position
watch(
	() => pageCanvas.value?.canvasProps.panning,
	() => {
		debouncedCursorUpdate(
			new MouseEvent("mousemove", {
				clientX: window.innerWidth / 2,
				clientY: window.innerHeight / 2,
			}),
		);
	},
	{ deep: true },
);

// Watch for block selection changes to sync with Yjs
watch(
	() => pageCanvas.value?.selectedBlockIds,
	(selectedIds) => {
		if (isCollaborationEnabled.value && yjsCollaboration.value && selectedIds) {
			// Convert Set to Array for Yjs
			yjsCollaboration.value.updateLocalSelection(Array.from(selectedIds));
		}
	},
	{ deep: true },
);

onDeactivated(() => {
	builderStore.realtime.doc_close("Builder Page", pageStore.activePage?.name as string);
	builderStore.realtime.off("doc_viewers", () => {});
	builderStore.viewers = [];

	// Remove mouse move listener
	document.removeEventListener("mousemove", debouncedCursorUpdate);
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
			!pageCanvas.value?.canvasProps?.settingCanvas
		) {
			pageStore.savingPage = true;
			debouncedPageSave();

			// Sync local changes with Yjs if collaboration is enabled and this is not a remote update
			if (
				isCollaborationEnabled.value &&
				!isRemoteUpdate.value &&
				yjsCollaboration.value &&
				pageCanvas.value?.block
			) {
				try {
					const blockData = getBlockString(pageCanvas.value.block);
					yjsCollaboration.value.updateLocalData({
						blocks: blockData,
						lastModified: new Date().toISOString(),
						modifiedBy: sessionUser.value,
					});
				} catch (error) {
					console.error("Error syncing with Yjs:", error);
				}
			}
		}
	},
	{
		deep: true,
	},
);

watch(
	() => canvasStore.showHTMLDialog,
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
	--left-panel-width: 17rem;
	--right-panel-width: 20rem;
	--toolbar-height: 3rem;
}
</style>
