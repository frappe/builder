<template>
	<div ref="canvasContainer" @click="handleClick">
		<slot name="header"></slot>
		<div class="overlay absolute" id="overlay" ref="overlay" />
		<Transition name="fade">
			<div
				class="absolute bottom-0 left-0 right-0 top-0 z-[19] grid w-full place-items-center bg-surface-gray-1 p-10 text-ink-gray-5"
				v-show="store.settingPage">
				<LoadingIcon></LoadingIcon>
			</div>
		</Transition>
		<BlockSnapGuides></BlockSnapGuides>
		<div
			v-if="isOverDropZone"
			class="pointer-events-none absolute bottom-0 left-0 right-0 top-0 z-30 bg-cyan-300 opacity-20"></div>
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
				class="canvas relative flex h-full rounded-md bg-surface-white shadow-2xl"
				:style="{
					...canvasStyles,
					background: canvasProps.background,
					width: `${breakpoint.width}px`,
				}"
				v-for="breakpoint in visibleBreakpoints"
				:key="breakpoint.device">
				<div
					class="absolute left-0 cursor-pointer select-none text-3xl text-gray-700 dark:text-zinc-300"
					:style="{
						fontSize: `calc(${12}px * 1/${canvasProps.scale})`,
						top: `calc(${-20}px * 1/${canvasProps.scale})`,
					}"
					v-show="!canvasProps.scaling && !canvasProps.panning"
					@click="store.activeBreakpoint = breakpoint.device">
					{{ breakpoint.displayName }}
				</div>
				<BuilderBlock
					class="h-full min-h-[inherit]"
					:block="block"
					:key="block.blockId"
					v-if="showBlocks"
					:breakpoint="breakpoint.device"
					:data="store.pageData" />
			</div>
		</div>
		<div
			class="fixed bottom-12 left-[50%] z-40 flex translate-x-[-50%] cursor-default items-center justify-center gap-2 rounded-lg bg-surface-white px-3 py-2 text-center text-sm font-semibold text-gray-600 shadow-md dark:text-zinc-400"
			v-show="!canvasProps.panning">
			{{ Math.round(canvasProps.scale * 100) + "%" }}
			<div class="ml-2 cursor-pointer" @click="setScaleAndTranslate">
				<FitScreenIcon />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import LoadingIcon from "@/components/Icons/Loading.vue";
import { BreakpointConfig, CanvasHistory } from "@/types/Builder/BuilderCanvas";
import Block from "@/utils/block";
import { getBlockCopy, isCtrlOrCmd } from "@/utils/helpers";
import { useBlockEventHandlers } from "@/utils/useBlockEventHandlers";
import { useBlockSelection } from "@/utils/useBlockSelection";
import { useCanvasDropZone } from "@/utils/useCanvasDropZone";
import { useCanvasEvents } from "@/utils/useCanvasEvents";
import { useCanvasUtils } from "@/utils/useCanvasUtils";
import { FeatherIcon } from "frappe-ui";
import { Ref, computed, onMounted, provide, reactive, ref, watch } from "vue";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import BuilderBlock from "./BuilderBlock.vue";
import FitScreenIcon from "./Icons/FitScreen.vue";

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);
const showBlocks = ref(false);
const overlay = ref(null);
const isDirty = ref(false);

const props = defineProps({
	blockData: {
		type: Block,
		default: false,
	},
	canvasStyles: {
		type: Object,
		default: () => ({}),
	},
});

// clone props.block into canvas data to avoid mutating them
const block = ref(getBlockCopy(props.blockData, true)) as Ref<Block>;
const history = ref(null) as Ref<null> | CanvasHistory;

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
} = useCanvasUtils(canvasProps, canvasContainer, canvas, block, selectedBlockIds, history);

const { isOverDropZone } = useCanvasDropZone(
	canvasContainer as unknown as Ref<HTMLElement>,
	block,
	findBlock,
);

const visibleBreakpoints = computed(() => {
	return canvasProps.breakpoints.filter((breakpoint) => breakpoint.visible);
});

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
	useBlockEventHandlers();
});

const handleClick = (ev: MouseEvent) => {
	const target = document.elementFromPoint(ev.clientX, ev.clientY);
	// hack to ensure if click is on canvas-container
	// TODO: Still clears selection if space handlers are dragged over canvas-container
	if (target?.classList.contains("canvas-container")) {
		clearSelection();
	}
};

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
	() => store.mode,
	(newValue, oldValue) => {
		store.lastMode = oldValue;
		toggleMode(store.mode);
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
}
</script>
