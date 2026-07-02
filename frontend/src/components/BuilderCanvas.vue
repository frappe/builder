<template>
	<div
		ref="canvasContainer"
		:data-builder-canvas="canvasId"
		@click="handleClick"
		@mousedown="handleMarqueeStart">
		<Transition name="fade">
			<div
				class="absolute bottom-0 left-0 right-0 top-0 grid w-full place-items-center bg-surface-gray-1 p-10 text-ink-gray-5"
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
				'--canvas-scale': canvasProps.scale,
			}">
			<div class="absolute right-0 top-[-60px] flex rounded-md bg-surface-base px-3">
				<Tooltip
					:text="scriptsDisabled ? 'Scripts are disabled in Builder Settings' : 'Run scripts in canvas'"
					:hoverDelay="0.6">
					<div
						data-testid="run-canvas-scripts"
						v-show="!canvasProps.scaling && !canvasProps.panning"
						class="w-auto p-2"
						:class="scriptsDisabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'"
						@click.stop="toggleCanvasScripts">
						<span
							:class="[
								builderStore.runCanvasScripts ? 'lucide-square' : 'lucide-play',
								'h-8 w-6 text-ink-gray-8',
							]"
							aria-hidden="true" />
					</div>
				</Tooltip>
				<Tooltip text="Refresh canvas scripts" :hoverDelay="0.6">
					<div
						data-testid="refresh-canvas-scripts"
						v-show="
							builderStore.runCanvasScripts &&
							!scriptsDisabled &&
							!canvasProps.scaling &&
							!canvasProps.panning
						"
						class="w-auto cursor-pointer p-2"
						@click.stop="refreshCanvasScripts">
						<span class="lucide-refresh-cw h-8 w-6 text-ink-gray-8" aria-hidden="true" />
					</div>
				</Tooltip>
				<div
					v-show="!canvasProps.scaling && !canvasProps.panning"
					class="m-2 my-3 w-px bg-[var(--outline-gray-2)]"></div>
				<Tooltip text="Toggle Canvas Dark Mode" :hoverDelay="0.6">
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
			<div
				class="relative bg-surface-base shadow-xl"
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
				<BuilderCanvasFrame
					:key="`${breakpoint.device}:${frameEpoch}`"
					:breakpoint="breakpoint.device"
					:width="breakpoint.width"
					:background="canvasProps.background"
					:canvas-id="canvasId"
					:canvas-styles="{ ...canvasStyles, '--canvas-scale': canvasProps.scale, cursor: cursorStyle }"
					:dark="builderStore.canvasDarkMode"
					@ready="registerFrame"
					@dispose="unregisterFrame">
					<component
						:is="'style'"
						v-if="pageClientStyles"
						data-builder-page-client-styles
						v-text="pageClientStyles" />
					<component
						:is="'style'"
						v-if="blockClientStyles"
						data-builder-client-styles
						v-text="blockClientStyles" />
					<BuilderBlock
						class="h-full min-h-[inherit]"
						:block="block"
						:style="variables"
						:key="block.blockId"
						:readonly="builderStore.readOnlyMode"
						v-if="showBlocks"
						:breakpoint="breakpoint.device"
						:data="pageStore.pageData" />
				</BuilderCanvasFrame>
			</div>
		</div>
		<div
			class="text-sm-semibold fixed bottom-12 left-[50%] flex translate-x-[-50%] cursor-default items-center justify-center gap-2 rounded-lg bg-surface-base px-3 py-2 text-center text-ink-gray-7 shadow-md"
			v-show="!canvasProps.panning">
			{{ Math.round(canvasProps.scale * 100) + "%" }}
			<div class="ml-2 cursor-pointer" @click="setScaleAndTranslate">
				<FitScreenIcon />
			</div>
		</div>
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
import BuilderCanvasFrame from "@/components/BuilderCanvasFrame.vue";
import DraggablePopup from "@/components/Controls/DraggablePopup.vue";
import SearchBlock from "@/components/Controls/SearchBlock.vue";
import LoadingIcon from "@/components/Icons/Loading.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BreakpointConfig, CanvasHistory, CanvasProps } from "@/types/Builder/BuilderCanvas";
import { elementFromEditorPoint, forwardFrameEvents } from "@/utils/canvasFrameDom";
import { getBlockObject, isCtrlOrCmd } from "@/utils/helpers";
import {
	type BlockClientScriptRuntime,
	executeClientScriptRestricted,
	executeClientScriptUnrestricted,
	executePageClientScriptRestricted,
	executePageClientScriptUnrestricted,
} from "@/utils/scriptSandbox";
import { useBlockEventHandlers } from "@/utils/useBlockEventHandlers";
import { useBlockSelection } from "@/utils/useBlockSelection";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useCanvasDropZone } from "@/utils/useCanvasDropZone";
import { useCanvasEvents } from "@/utils/useCanvasEvents";
import { useCanvasMarqueeSelection } from "@/utils/useCanvasMarqueeSelection";
import { useCanvasUtils } from "@/utils/useCanvasUtils";
import { Tooltip } from "frappe-ui";
import {
	type EffectScope,
	Ref,
	computed,
	effectScope,
	nextTick,
	onMounted,
	onUnmounted,
	provide,
	reactive,
	ref,
	useId,
	watch,
} from "vue";
import setPanAndZoom from "../utils/panAndZoom";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import BuilderBlock from "./BuilderBlock.vue";
import FitScreenIcon from "./Icons/FitScreen.vue";

const builderStore = useBuilderStore();
const pageStore = usePageStore();
const canvasId = `builder-canvas-${useId()}`;

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
const blockStyles = reactive(new Map<string, string>());
const frameRoots = reactive(new Map<string, HTMLElement>());
const frameEpoch = ref(0);
const frameRegistrations = new Map<
	string,
	{ document: Document; scope: EffectScope; stopForwarding: () => void }
>();
const cursorStyle = ref("default");

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
const blockClientStyles = computed(() => {
	const css = Array.from(blockStyles.values()).filter(Boolean).join("\n");
	return css ? `@layer builder-authored {\n${css}\n}` : "";
});
const pageClientStyles = computed(() =>
	pageStore.activePageScripts
		.filter((script) => script.script_type === "CSS")
		.map((script) => script.script)
		.filter(Boolean)
		.join("\n"),
);
const pageJavaScripts = computed(() =>
	pageStore.activePageScripts.filter((script) => script.script_type === "JavaScript"),
);
const pageJavaScriptSignature = computed(() =>
	JSON.stringify(pageJavaScripts.value.map(({ name, script }) => [name, script])),
);
const pageDataSignature = computed(() => JSON.stringify(pageStore.pageData));
const scriptsDisabled = computed(
	() => builderSettings.doc?.execute_block_scripts_in_editor === "Don't Execute",
);

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

const canvasProps = reactive<CanvasProps>({
	background: "#fff",
	scale: 1,
	translateX: 0,
	translateY: 0,
	settingCanvas: true,
	scaling: false,
	panning: false,
	frameRoots,
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
		frameRoots,
		canvasProps,
		activeBreakpoint,
		selectedBlockIds,
		findBlock,
		setActiveBreakpoint,
		setHoveredBreakpoint,
	});

onMounted(() => {
	const canvasContainerEl = canvasContainer.value as unknown as HTMLElement;
	const canvasEl = canvas.value as unknown as HTMLElement;
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
	frameRegistrations.forEach(({ document }, breakpoint) => unregisterFrame(breakpoint, document));
});

const handleClick = (ev: MouseEvent) => {
	if (suppressNextClick.value) {
		suppressNextClick.value = false;
		return;
	}

	const target = elementFromEditorPoint(ev.clientX, ev.clientY);
	// hack to ensure if click is on canvas-container
	// TODO: Still clears selection if space handlers are dragged over canvas-container
	if (target?.classList.contains("canvas-container")) {
		clearSelection();
	}
};

function registerFrame(breakpoint: string, doc: Document, root: HTMLElement, iframe: HTMLIFrameElement) {
	unregisterFrame(breakpoint);
	frameRoots.set(breakpoint, root);

	const scope = effectScope();
	frameRegistrations.set(breakpoint, {
		document: doc,
		scope,
		stopForwarding: forwardFrameEvents(doc, iframe),
	});
	scope.run(() => {
		const { isOverDropZone } = useCanvasDropZone(ref(doc.body), block, findBlock);
		watch(isOverDropZone, (isOver) => root.toggleAttribute("data-drop-active", isOver), { immediate: true });
		watch(
			[() => builderStore.runCanvasScripts, () => pageStore.settingPage],
			([runScripts, settingPage], _, onCleanup) => {
				if (!runScripts || settingPage || scriptsDisabled.value) return;
				onCleanup(executePageClientScripts(root));
			},
			{ immediate: true, flush: "post" },
		);
	});
	nextTick(setScaleAndTranslate);
}

function unregisterFrame(breakpoint: string, doc: Document | null = null) {
	const registration = frameRegistrations.get(breakpoint);
	if (doc && registration && registration.document !== doc) return;

	registration?.stopForwarding();
	registration?.scope.stop();
	frameRegistrations.delete(breakpoint);
	frameRoots.get(breakpoint)?.removeAttribute("data-drop-active");
	frameRoots.delete(breakpoint);
}

onMounted(() => {
	if (!canvasContainer.value) return;

	const observer = new MutationObserver(() => {
		cursorStyle.value = canvasContainer.value?.style.cursor || "default";
	});

	observer.observe(canvasContainer.value, {
		attributes: true,
		attributeFilter: ["style"],
	});

	onUnmounted(() => observer.disconnect());
});

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

watch(
	() => builderSettings.doc?.execute_block_scripts_in_editor,
	(mode, previousMode) => {
		const scriptsWereRunning = builderStore.runCanvasScripts;
		if (mode === "Don't Execute" && scriptsWereRunning) {
			builderStore.runCanvasScripts = false;
		}
		if (previousMode && mode !== previousMode && scriptsWereRunning) {
			frameEpoch.value++;
		}
	},
);

watch(
	[pageJavaScriptSignature, pageDataSignature],
	([scriptSignature, dataSignature], [previousScriptSignature, previousDataSignature]) => {
		if (
			(scriptSignature === previousScriptSignature && dataSignature === previousDataSignature) ||
			!pageJavaScripts.value.length ||
			!builderStore.runCanvasScripts ||
			pageStore.settingPage ||
			scriptsDisabled.value
		)
			return;
		frameEpoch.value++;
	},
);

watch(
	() => pageStore.settingPage,
	(settingPage, wasSettingPage) => {
		if (!settingPage && wasSettingPage && builderStore.runCanvasScripts && !scriptsDisabled.value) {
			frameEpoch.value++;
		}
	},
);

provide("canvasProps", canvasProps);
provide("emulateBlockClientScript", emulateBlockClientScript);

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

function toggleCanvasScripts() {
	if (scriptsDisabled.value) return;
	builderStore.runCanvasScripts = !builderStore.runCanvasScripts;
	frameEpoch.value++;
}

function refreshCanvasScripts() {
	if (!builderStore.runCanvasScripts || scriptsDisabled.value) return;
	frameEpoch.value++;
}

function escapeAttributeValue(value: string) {
	return value.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

function emulateBlockClientScript(script: BlockClientScriptRuntime) {
	const registrationKey = `${script.key}:${script.breakpoint}`;
	const selector = `[data-builder-canvas="${canvasId}"] [data-block-uid="${escapeAttributeValue(
		script.key,
	)}"][data-breakpoint="${escapeAttributeValue(script.breakpoint)}"]`;
	blockStyles.set(registrationKey, script.css ? `${selector} { ${script.css} }` : "");

	const mode = builderSettings.doc?.execute_block_scripts_in_editor ?? "Restricted";
	let cleanup = () => {};
	if (builderStore.runCanvasScripts && mode !== "Don't Execute" && script.javascript.trim()) {
		const context = {
			componentData: script.componentData,
			props: script.props,
		};
		cleanup =
			mode === "Unrestricted"
				? executeClientScriptUnrestricted(script.element, script.javascript, context)
				: executeClientScriptRestricted(
						script.element,
						frameRoots.get(script.breakpoint) || null,
						script.javascript,
						context,
				  );
	}

	return () => {
		try {
			cleanup();
		} finally {
			blockStyles.delete(registrationKey);
		}
	};
}

function executePageClientScripts(root: HTMLElement) {
	const mode = builderSettings.doc?.execute_block_scripts_in_editor ?? "Restricted";
	const cleanups = pageJavaScripts.value.map(({ script }) =>
		mode === "Unrestricted"
			? executePageClientScriptUnrestricted(root, script, pageStore.pageData)
			: executePageClientScriptRestricted(root, script, pageStore.pageData),
	);

	return () => {
		cleanups.reverse().forEach((cleanup) => cleanup());
	};
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

.canvas[data-drop-active] > .editor {
	pointer-events: none;
}
</style>
