<template>
	<div ref="canvasContainer" @click="handleClick" @mousedown="handleMarqueeStart">
		<Transition name="fade">
			<div
				class="absolute bottom-0 left-0 right-0 top-0 grid w-full place-items-center bg-surface-gray-1 p-10 text-ink-gray-5"
				v-show="pageStore.settingPage">
				<LoadingIcon></LoadingIcon>
			</div>
		</Transition>
		<BlockSnapGuides v-if="!builderStore.showPagePreview"></BlockSnapGuides>
		<div
			class="fixed flex gap-40"
			:class="{
				'scheme-dark': builderStore.canvasDarkMode && !builderStore.showPagePreview,
			}"
			ref="canvas"
			:style="{
				transformOrigin: 'top center',
				transform: `scale(${canvasProps.scale}) translate(${canvasProps.translateX}px, ${canvasProps.translateY}px)`,
				'--canvas-scale': canvasProps.scale,
				colorScheme: builderStore.canvasDarkMode ? 'dark' : 'light',
			}">
			<div class="absolute right-0 top-[-60px] flex rounded-md bg-surface-base px-3">
				<Tooltip v-if="showPagePreviewToggle" text="Toggle Page Preview" :hoverDelay="0.6">
					<div
						v-show="!canvasProps.scaling && !canvasProps.panning"
						class="w-auto cursor-pointer p-2"
						@click.stop="togglePagePreview">
						<span
							:class="[
								builderStore.showPagePreview ? 'lucide-mouse-pointer' : 'lucide-play',
								'h-8 w-6 text-ink-gray-8',
							]"
							aria-hidden="true" />
					</div>
				</Tooltip>
				<div
					v-if="showPagePreviewToggle"
					v-show="!canvasProps.scaling && !canvasProps.panning"
					class="m-2 my-3 w-px bg-[var(--outline-gray-2)]"></div>
				<Tooltip
					:text="builderStore.showPagePreview ? 'Toggle Preview Color Scheme' : 'Toggle Canvas Dark Mode'"
					:hoverDelay="0.6">
					<div
						v-show="!canvasProps.scaling && !canvasProps.panning"
						class="w-auto cursor-pointer p-2"
						@click.stop="builderStore.canvasDarkMode = !builderStore.canvasDarkMode">
						<span
							:class="[builderStore.canvasDarkMode ? 'lucide-sun' : 'lucide-moon', 'h-8 w-6 text-ink-gray-8']"
							aria-hidden="true" />
					</div>
				</Tooltip>
				<div
					v-show="!canvasProps.scaling && !canvasProps.panning"
					class="m-2 my-3 w-px bg-[var(--outline-gray-2)]"></div>
				<div
					v-show="!canvasProps.scaling && !canvasProps.panning"
					class="w-auto cursor-pointer p-2"
					v-for="breakpoint in canvasProps.breakpoints"
					:key="breakpoint.device"
					@click.stop="(ev) => selectBreakpoint(ev, breakpoint)">
					<span
						:class="[
							breakpoint.icon,
							'h-8 w-6',
							{ 'text-ink-gray-8': breakpoint.visible, 'text-ink-gray-3': !breakpoint.visible },
						]"
						aria-hidden="true" />
				</div>
			</div>
			<template v-if="builderStore.showPagePreview">
				<div
					class="canvas relative bg-surface-base shadow-2xl"
					:data-breakpoint="breakpoint.device"
					:style="{
						...canvasStyles,
						width: `${breakpoint.width}px`,
						height: previewHeights[breakpoint.device] || '200px',
					}"
					v-for="breakpoint in renderedBreakpoints"
					v-show="breakpoint.visible"
					:key="`preview-${breakpoint.device}`">
					<div
						class="absolute left-0 cursor-pointer select-none text-5xl text-ink-gray-7"
						:style="{
							fontSize: `calc(${12}px * 1/${canvasProps.scale})`,
							top: `calc(${-20}px * 1/${canvasProps.scale})`,
						}"
						v-show="!canvasProps.scaling && !canvasProps.panning"
						@click="activeBreakpoint = breakpoint.device">
						{{ breakpoint.displayName }}
					</div>
					<iframe
						v-if="previewUrl"
						:src="previewUrl"
						:key="`${breakpoint.device}-${previewRefreshKey}`"
						:ref="(el) => setPreviewIframe(breakpoint.device, el as HTMLIFrameElement | null)"
						frameborder="0"
						:sandbox="PREVIEW_IFRAME_SANDBOX"
						data-builder-preview-iframe
						class="w-full rounded-sm"
						style="display: block; height: 100%"
						@load="onIframeLoad(breakpoint.device)" />
					<div
						v-show="previewLoading[breakpoint.device]"
						class="absolute inset-0 z-20 grid place-items-center bg-surface-gray-1/80 text-ink-gray-5">
						<LoadingIcon />
					</div>
					<div
						v-show="builderStore.previewIframeScrollHeld"
						class="absolute inset-0 z-10"
						aria-hidden="true" />
				</div>
			</template>
			<template v-else>
				<div
					class="canvas relative flex h-full bg-surface-base shadow-2xl contain-layout"
					:data-breakpoint="breakpoint.device"
					:style="{
						...canvasStyles,
						background: canvasProps.background,
						width: `${breakpoint.width}px`,
					}"
					v-for="breakpoint in renderedBreakpoints"
					v-show="breakpoint.visible"
					:key="breakpoint.device">
					<div
						class="absolute left-0 cursor-pointer select-none text-5xl text-ink-gray-7"
						:style="{
							fontSize: `calc(${12}px * 1/${canvasProps.scale})`,
							top: `calc(${-20}px * 1/${canvasProps.scale})`,
						}"
						v-show="!canvasProps.scaling && !canvasProps.panning"
						@click="activeBreakpoint = breakpoint.device">
						{{ breakpoint.displayName }}
					</div>
					<BuilderBlock
						class="h-full min-h-[inherit]"
						:block="block"
						:style="variables"
						:key="block.blockId"
						:readonly="builderStore.readOnlyMode"
						v-if="showBlocks"
						:breakpoint="breakpoint.device"
						:data="pageStore.pageData" />
				</div>
			</template>
		</div>
		<div
			class="text-sm-semibold fixed bottom-12 left-[50%] flex translate-x-[-50%] cursor-default items-center justify-center gap-2 rounded-lg bg-surface-base px-3 py-2 text-center text-ink-gray-7 shadow-md"
			v-show="!canvasProps.panning">
			{{ Math.round(canvasProps.scale * 100) + "%" }}
			<div class="ml-2 cursor-pointer" @click="setScaleAndTranslate">
				<FitScreenIcon />
			</div>
		</div>
		<div
			class="overlay absolute"
			:class="{ 'pointer-events-none': isOverDropZone }"
			id="overlay"
			ref="overlay" />
		<div v-show="marquee.visible" class="pointer-events-none fixed z-[200]" :style="marqueeStyle" />
		<div class="absolute top-0 order-1 w-full">
			<slot name="header"></slot>
		</div>
		<DraggablePopup
			v-model="builderStore.showSearchBlock"
			:container="canvasContainer"
			placement="top-right"
			:placementOffset="20"
			v-if="builderStore.showSearchBlock">
			<template #header>Search Block</template>
			<template #content>
				<SearchBlock></SearchBlock>
			</template>
		</DraggablePopup>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import DraggablePopup from "@/components/Controls/DraggablePopup.vue";
import SearchBlock from "@/components/Controls/SearchBlock.vue";
import LoadingIcon from "@/components/Icons/Loading.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BreakpointConfig, CanvasHistory } from "@/types/Builder/BuilderCanvas";
import { getBlockObject, isCtrlOrCmd } from "@/utils/helpers";
import { useBlockEventHandlers } from "@/utils/useBlockEventHandlers";
import { useBlockSelection } from "@/utils/useBlockSelection";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useCanvasDropZone } from "@/utils/useCanvasDropZone";
import { useCanvasEvents } from "@/utils/useCanvasEvents";
import { useCanvasMarqueeSelection } from "@/utils/useCanvasMarqueeSelection";
import { useCanvasUtils } from "@/utils/useCanvasUtils";
import { PREVIEW_IFRAME_SANDBOX, usePagePreview } from "@/utils/usePagePreview";
import { Tooltip } from "frappe-ui";
import { Ref, computed, onMounted, onUnmounted, provide, reactive, ref, watch } from "vue";
import setPanAndZoom from "../utils/panAndZoom";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import BuilderBlock from "./BuilderBlock.vue";
import FitScreenIcon from "./Icons/FitScreen.vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

const shouldForwardPreviewKeys = (event: KeyboardEvent) => {
	if (event.key === "Alt") return true;
	if (event.key === "p" && (event.ctrlKey || event.metaKey)) return true;
	return false;
};

const {
	previewUrl,
	refreshKey: previewRefreshKey,
	previewLoading,
	previewHeights,
	setPreviewIframe,
	onIframeLoad,
} = usePagePreview(shouldForwardPreviewKeys);

const showPagePreviewToggle = computed(
	() => canvasStore.editingMode === "page" && !canvasStore.versionPreviewBlock,
);

function togglePagePreview() {
	builderStore.showPagePreview = !builderStore.showPagePreview;
}

const { cssVariables, darkCssVariables } = useBuilderVariable();

const variables = computed(() => {
	return {
		...cssVariables.value,
		...(builderStore.canvasDarkMode ? darkCssVariables.value : {}),
	};
});

const resizingBlock = ref(false);
const canvasContainer = ref(null) as Ref<HTMLElement | null>;
const canvas = ref(null);
const showBlocks = ref(false);
const overlay = ref(null);

const props = withDefaults(
	defineProps<{
		blockData: Block | BlockOptions;
		canvasStyles?: Record<string, any>;
	}>(),
	{
		canvasStyles: () => ({}),
	},
);

const block = ref(props.blockData) as Ref<Block>;
const history = ref(null) as Ref<null> | CanvasHistory;

const activeBreakpoint = ref("desktop") as Ref<string | null>;
const hoveredBreakpoint = ref("desktop") as Ref<string | null>;
const hoveredBlock = ref(null) as Ref<string | null>;
const setCanvasZoom = ref<(scale: number, pinchPoint: { x: number; y: number } | "center") => void>();

const {
	clearSelection,
	selectBlockRange,
	selectedBlockIds,
	isSelected,
	toggleBlockSelection,
	selectedBlocks,
} = useBlockSelection(block);

const canvasProps = reactive({
	overlayElement: null,
	background: "#fff",
	scale: 1,
	translateX: 0,
	translateY: 0,
	settingCanvas: true,
	scaling: false,
	panning: false,
	breakpoints: [
		{
			icon: "lucide-monitor",
			device: "desktop",
			displayName: "Desktop",
			width: 1400,
			visible: true,
			renderedOnce: true,
		},
		{
			icon: "lucide-tablet",
			device: "tablet",
			displayName: "Tablet",
			width: 800,
			visible: false,
		},
		{
			icon: "lucide-smartphone",
			device: "mobile",
			displayName: "Mobile",
			width: 420,
			visible: false,
		},
	] as BreakpointConfig[],
});

const {
	setScaleAndTranslate,
	resetZoom,
	moveCanvas,
	zoomIn,
	zoomOut,
	toggleMode,
	toggleDirty,
	setupHistory,
	clearCanvas,
	getRootBlock,
	setRootBlock,
	selectBlock,
	scrollBlockIntoView,
	removeBlock,
	findBlock,
	isDirty,
} = useCanvasUtils(canvasProps, canvasContainer, canvas, block, selectedBlockIds, history);

const { marquee, marqueeStyle, suppressNextClick, handleMarqueeStart, cleanupMarqueeListeners } =
	useCanvasMarqueeSelection({
		canvasContainer,
		canvasProps,
		activeBreakpoint,
		selectedBlockIds,
		findBlock,
		setActiveBreakpoint,
		setHoveredBreakpoint,
	});

const { isOverDropZone } = useCanvasDropZone(
	canvasContainer as unknown as Ref<HTMLElement>,
	block,
	findBlock,
);

onMounted(() => {
	const canvasContainerEl = canvasContainer.value as unknown as HTMLElement;
	const canvasEl = canvas.value as unknown as HTMLElement;
	canvasProps.overlayElement = overlay.value;
	setScaleAndTranslate();
	showBlocks.value = true;
	setupHistory();
	// a read-only canvas (version preview / protected page) fully disables history;
	// editing the canvas re-enables it
	watch(
		() => builderStore.readOnlyMode,
		(readOnly) => (readOnly ? history.value?.disable() : history.value?.enable()),
		{ immediate: true },
	);
	useCanvasEvents(
		canvasContainer as unknown as Ref<HTMLElement>,
		canvasProps,
		history as CanvasHistory,
		selectedBlocks,
		getRootBlock,
		findBlock,
	);
	const { setZoom } = setPanAndZoom(canvasEl, canvasContainerEl, canvasProps);
	setCanvasZoom.value = setZoom;
	useBlockEventHandlers(canvasContainerEl);
});

onUnmounted(() => {
	cleanupMarqueeListeners();
});

const handleClick = (ev: MouseEvent) => {
	if (builderStore.showPagePreview) {
		return;
	}

	if (suppressNextClick.value) {
		suppressNextClick.value = false;
		return;
	}

	const target = document.elementFromPoint(ev.clientX, ev.clientY);
	// hack to ensure if click is on canvas-container
	// TODO: Still clears selection if space handlers are dragged over canvas-container
	if (target?.classList.contains("canvas-container")) {
		clearSelection();
	}
};

function searchBlock(searchTerm: string, targetBlock: null | Block, limit: number = 5): Block[] {
	const results: Block[] = [];

	function search(block: Block) {
		if (results.length >= limit) return;

		const blockObject = getBlockObject(block);
		const children = blockObject.children || [];
		delete blockObject.children;

		if (JSON.stringify(blockObject).toLowerCase().includes(searchTerm.toLowerCase())) {
			results.push(findBlock(block.blockId) as Block);
		}

		for (const child of children) {
			search(child);
		}
	}

	if (!targetBlock) {
		targetBlock = getRootBlock();
	}

	search(targetBlock);
	return results;
}

function setActiveBreakpoint(breakpoint: string | null) {
	activeBreakpoint.value = breakpoint;
}

function setHoveredBreakpoint(breakpoint: string | null) {
	hoveredBreakpoint.value = breakpoint;
}

function setHoveredBlock(blockId: string | null) {
	hoveredBlock.value = blockId;
}

watch(
	() => block,
	() => {
		toggleDirty(true);
	},
	{
		deep: true,
	},
);

watch(
	() => canvasProps.breakpoints.map((b) => b.visible),
	() => {
		if (canvasProps.settingCanvas) {
			return;
		}
		setScaleAndTranslate();
	},
);

watch(
	() => builderStore.mode,
	(newValue, oldValue) => {
		builderStore.lastMode = oldValue;
		toggleMode(builderStore.mode);
	},
);

provide("canvasProps", canvasProps);

defineExpose({
	setScaleAndTranslate,
	resetZoom,
	moveCanvas,
	zoomIn,
	zoomOut,
	history,
	clearCanvas,
	getRootBlock,
	block,
	setRootBlock,
	canvasProps,
	selectBlock,
	toggleBlockSelection,
	selectedBlocks,
	clearSelection,
	isSelected,
	selectedBlockIds,
	findBlock,
	isDirty,
	toggleDirty,
	scrollBlockIntoView,
	removeBlock,
	selectBlockRange,
	resizingBlock,
	searchBlock,
	activeBreakpoint,
	hoveredBreakpoint,
	hoveredBlock,
	setActiveBreakpoint,
	setHoveredBreakpoint,
	setHoveredBlock,
	setCanvasZoom,
});

function selectBreakpoint(ev: MouseEvent, breakpoint: BreakpointConfig) {
	if (isCtrlOrCmd(ev)) {
		canvasProps.breakpoints.forEach((bp) => {
			bp.visible = bp.device === breakpoint.device;
		});
	} else {
		breakpoint.visible = !breakpoint.visible;
		if (canvasProps.breakpoints.filter((bp) => bp.visible).length === 0) {
			breakpoint.visible = true;
		}
	}
	if (breakpoint.visible) {
		hoveredBreakpoint.value = breakpoint.device;
		activeBreakpoint.value = breakpoint.device;
		breakpoint.renderedOnce = true;
	}
	const isActiveVisible = canvasProps.breakpoints.find(
		(bp) => bp.device === activeBreakpoint.value && bp.visible,
	);
	if (!isActiveVisible) {
		const lastVisible = Array.from(canvasProps.breakpoints)
			.reverse()
			.find((bp) => bp.visible);
		if (lastVisible) {
			activeBreakpoint.value = lastVisible.device;
			hoveredBreakpoint.value = lastVisible.device;
		}
	}
}

const renderedBreakpoints = computed(() => canvasProps.breakpoints.filter((bp) => bp.renderedOnce));
</script>
<style>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.1s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}

#placeholder {
	@apply transition-all;
}
.vertical-placeholder {
	@apply mx-4 h-full min-h-5 w-auto border-l-2 border-dashed border-blue-500;
}
.horizontal-placeholder {
	@apply my-4 h-auto w-full border-t-2 border-dashed border-blue-500;
}

/* Lightweight marquee-drag highlight — applied via DOM attribute, not Vue reactive state */
.__builder_component__[data-marquee-selected] {
	box-shadow: inset 0 0 0 calc(2px / var(--canvas-scale, 1)) theme("colors.blue.400 / 85%");
}

.canvas-container {
	p:not(:where(.prose, .ProseMirror) *) {
		line-height: revert;
	}
}
</style>
