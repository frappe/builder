<template>
	<div
		ref="canvasContainer"
		:style="{
			left: `${store.builderLayout.leftPanelWidth}px`,
			right: `${store.builderLayout.rightPanelWidth}px`,
		}">
		<div class="overlay absolute" id="overlay" />
		<BlockSnapGuides />
		<div
			class="fixed flex"
			ref="canvas"
			:style="{
				transform: `scale(${store.canvas.scale}) translate(${store.canvas.translateX}px, ${store.canvas.translateY}px)`,
				minHeight: '1400px',
				height: '100%',
			}">
			<div class="absolute top-[-60px] right-0 flex h-fit rounded-md bg-white px-3 dark:bg-zinc-900">
				<div
					class="w-auto cursor-pointer p-2"
					v-for="breakpoint in store.deviceBreakpoints"
					:key="breakpoint.device"
					@click.stop="breakpoint.visible = !breakpoint.visible">
					<FeatherIcon
						:name="breakpoint.icon"
						class="h-8 w-6"
						:class="{
							'text-gray-700 dark:text-zinc-50': breakpoint.visible,
							'text-gray-300 dark:text-zinc-500': !breakpoint.visible,
						}" />
				</div>
			</div>
			<div
				class="canvas relative ml-20 h-full rounded-md bg-white"
				:style="{
					background: store.canvas.background,
					width: breakpoint.width + 'px',
				}"
				v-for="breakpoint in visibleBreakpoints"
				:key="breakpoint.device">
				<BuilderBlock
					:block="store.builderState.blocks[0]"
					v-if="showBlocks"
					:breakpoint="breakpoint.device" />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { nextTick, onMounted, ref, computed, watch, reactive } from "vue";
import { useElementBounding } from "@vueuse/core";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BuilderBlock from "./BuilderBlock.vue";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import { useDebouncedRefHistory } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { FeatherIcon, toast } from "frappe-ui";
import Block from "@/utils/block";

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);
const showBlocks = ref(false);

function getPageData() {
	return store.builderState.blocks;
}
store.getPageData = getPageData;

const clearSelectedComponent = () => {
	store.builderState.selectedBlock = null;
	store.builderState.selectedBlocks = [];
	if (document.activeElement instanceof HTMLElement) {
		document.activeElement.blur();
	}
};

const visibleBreakpoints = computed(() => {
	return store.deviceBreakpoints.filter(
		(breakpoint) => breakpoint.visible || breakpoint.device === "desktop"
	);
});

document.addEventListener("keydown", (e) => {
	const target = e.target as HTMLElement;
	if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
		return;
	}
	if (
		e.key === "Backspace" &&
		store.builderState.selectedBlock &&
		!target.closest(".__builder_component__")
	) {
		function findBlockAndRemove(blocks: Array<Block>, blockId: string) {
			if (blockId === "root") {
				toast({
					title: "Warning",
					text: "Cannot Delete Root Block",
					icon: "alert-circle",
					iconClasses: "text-yellow-500",
					position: "top-left",
				});
				return false;
			}
			blocks.forEach((block, i) => {
				if (block.blockId === blockId) {
					blocks.splice(i, 1);
					return true;
				} else if (block.children) {
					return findBlockAndRemove(block.children, blockId);
				}
			});
		}
		findBlockAndRemove(store.builderState.blocks, store.builderState.selectedBlock.blockId);
		clearSelectedComponent();
	}

	if (e.key === "Escape") {
		clearSelectedComponent();
	}
});

const containerBound = reactive(useElementBounding(canvasContainer));
const canvasBound = reactive(useElementBounding(canvas));

const setScaleAndTranslate = async () => {
	const paddingX = 300;
	const paddingY = 400;
	store.canvas.scale = 1;
	store.canvas.translateX = 0;
	store.canvas.translateY = 0;

	await nextTick();
	canvasBound.update();
	const containerWidth = containerBound.width;
	const containerHeight = containerBound.height;
	store.canvas.initialScale = store.canvas.scale = Math.min(
		containerWidth / (canvasBound.width + paddingX * 2),
		containerHeight / (canvasBound.height + paddingY * 2)
	);

	await nextTick();
	const scale = store.canvas.scale;
	canvasBound.update();
	const diffY = containerBound.top - canvasBound.top + paddingY * scale;
	if (diffY !== 0) {
		store.canvas.initialTranslateY = store.canvas.translateY = diffY / scale;
	}
	showBlocks.value = true;
};

onMounted(() => {
	setScaleAndTranslate();
	const canvasContainerEl = canvasContainer.value as unknown as HTMLElement;
	const canvasEl = canvas.value as unknown as HTMLElement;
	setPanAndZoom(store.canvas, canvasEl, canvasContainerEl);
	const { builderState } = storeToRefs(store);
	const { undo, redo, canUndo, canRedo } = useDebouncedRefHistory(builderState, {
		capacity: 100,
		deep: true,
		clone: (obj) => {
			let newObj = Object.assign({}, obj);
			newObj.blocks = obj.blocks.map((val) => store.getBlockCopy(val, true));
			if (obj.selectedBlock) {
				newObj.selectedBlock = findBlock(newObj.blocks, obj.selectedBlock.blockId);
			}
			return newObj;
		},
		debounce: 200,
	});

	document.addEventListener("keydown", (e) => {
		const target = e.target as HTMLElement;
		if (
			target.tagName === "INPUT" ||
			target.tagName === "TEXTAREA" ||
			target.getAttribute("contenteditable")
		) {
			return;
		}
		if (e.key === "z" && e.metaKey && !e.shiftKey && canUndo.value) {
			undo();
			e.preventDefault();
		}
		if (e.key === "z" && e.shiftKey && e.metaKey && canRedo.value) {
			redo();
			e.preventDefault();
		}
	});

	function findBlock(blocks: Array<Block>, blockId: string): Block | null {
		for (const block of blocks) {
			if (block.blockId === blockId) {
				return block;
			}
			if (block.children) {
				const found = findBlock(block.children, blockId);
				if (found) {
					return found;
				}
			}
		}
		return null;
	}
});

watch(store.deviceBreakpoints, setScaleAndTranslate, { deep: true });
</script>
