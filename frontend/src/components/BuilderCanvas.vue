<template>
	<div ref="canvasContainer" @click="handleClick">
		<slot name="header"></slot>
		<div
			class="overlay absolute"
			:class="{ 'pointer-events-none': isOverDropZone }"
			id="overlay"
			ref="overlay" />
		<Transition name="fade">
			<div
				class="absolute bottom-0 left-0 right-0 top-0 z-[19] grid w-full place-items-center bg-surface-gray-1 p-10 text-ink-gray-5"
				v-show="pageStore.settingPage">
				<LoadingIcon></LoadingIcon>
			</div>
		</Transition>
		<BlockSnapGuides></BlockSnapGuides>
		<div
			class="fixed flex gap-40"
			ref="canvas"
			:style="{
				transformOrigin: 'top center',
				transform: `scale(${canvasProps.scale}) translate(${canvasProps.translateX}px, ${canvasProps.translateY}px)`,
			}">
			<div class="absolute right-0 top-[-60px] flex rounded-md bg-surface-white px-3">
				<div
					v-show="!canvasProps.scaling && !canvasProps.panning"
					class="w-auto cursor-pointer p-2"
					v-for="breakpoint in canvasProps.breakpoints"
					:key="breakpoint.device"
					@click.stop="(ev) => selectBreakpoint(ev, breakpoint)">
					<FeatherIcon
						:name="breakpoint.icon"
						class="h-8 w-6"
						:class="{
							'text-ink-gray-8': breakpoint.visible,
							'text-ink-gray-3': !breakpoint.visible,
						}" />
				</div>
			</div>
			<div
				class="canvas relative flex h-full bg-surface-white shadow-2xl contain-layout dark:selection:!bg-gray-200"
				:style="{
					...canvasStyles,
					background: canvasProps.background,
					width: `${breakpoint.width}px`,
				}"
				v-for="breakpoint in renderedBreakpoints"
				v-show="breakpoint.visible"
				:key="breakpoint.device">
				<div
					class="absolute left-0 cursor-pointer select-none text-3xl text-ink-gray-7"
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
					:style="cssVariables"
					:key="block.blockId"
					v-if="showBlocks"
					:breakpoint="breakpoint.device"
					:data="pageStore.pageData" />
			</div>
		</div>
		<div
			class="fixed bottom-12 left-[50%] z-40 flex translate-x-[-50%] cursor-default items-center justify-center gap-2 rounded-lg bg-surface-white px-3 py-2 text-center text-sm font-semibold text-ink-gray-7 shadow-md"
			v-show="!canvasProps.panning">
			{{ Math.round(canvasProps.scale * 100) + "%" }}
			<div class="ml-2 cursor-pointer" @click="setScaleAndTranslate">
				<FitScreenIcon />
			</div>
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
import usePageStore from "@/stores/pageStore";
import { BreakpointConfig, CanvasHistory } from "@/types/Builder/BuilderCanvas";
import { getBlockObject, isCtrlOrCmd } from "@/utils/helpers";
import { useBlockEventHandlers } from "@/utils/useBlockEventHandlers";
import { useBlockSelection } from "@/utils/useBlockSelection";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useCanvasDropZone } from "@/utils/useCanvasDropZone";
import { useCanvasEvents } from "@/utils/useCanvasEvents";
import { useCanvasUtils } from "@/utils/useCanvasUtils";
import { FeatherIcon } from "frappe-ui";
import { Ref, computed, onMounted, provide, reactive, ref, watch } from "vue";
import setPanAndZoom from "../utils/panAndZoom";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import BuilderBlock from "./BuilderBlock.vue";
import FitScreenIcon from "./Icons/FitScreen.vue";

const builderStore = useBuilderStore();
const pageStore = usePageStore();

const { cssVariables } = useBuilderVariable();

const resizingBlock = ref(false);
const canvasContainer = ref(null) as Ref<HTMLElement | null>;
const canvas = ref(null);
const showBlocks = ref(false);
const overlay = ref(null);

const props = withDefaults(
	defineProps<{
		blockData: Block;
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
			icon: "monitor",
			device: "desktop",
			displayName: "Desktop",
			width: 1400,
			visible: true,
			renderedOnce: true,
		},
		{
			icon: "tablet",
			device: "tablet",
			displayName: "Tablet",
			width: 800,
			visible: false,
		},
		{
			icon: "smartphone",
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
	useCanvasEvents(
		canvasContainer as unknown as Ref<HTMLElement>,
		canvasProps,
		history as CanvasHistory,
		selectedBlocks,
		getRootBlock,
		findBlock,
	);
	setPanAndZoom(canvasEl, canvasContainerEl, canvasProps);
	useBlockEventHandlers(canvasContainerEl);
});

const handleClick = (ev: MouseEvent) => {
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
</style>
