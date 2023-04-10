<template>
	<div
		ref="canvasContainer"
		:style="{
			left: `${store.builderLayout.leftPanelWidth}px`,
			right: `${store.builderLayout.rightPanelWidth}px`,
		}">
		<div class="absolute" id="block-draggables" />
		<div class="overlay absolute" id="overlay" />
		<BlockSnapGuides />
		<div class="fixed flex" ref="canvas"
			:style="{
				transform: `scale(${store.canvas.scale}) translate(${store.canvas.translateX}px, ${store.canvas.translateY}px)`,
				minHeight: '1400px',
				height: '100%',
			}">
			<div
				class="canvas rounded-md bg-white ml-20 h-full relative"
				:style="{
					background: store.canvas.background,
					width: value.width + 'px',
				}"
				v-for="(value, breakpoint) in store.deviceBreakpoints"
				:key="breakpoint">
				<BuilderBlock :element-properties="store.builderState.blocks[0]" v-if="showBlocks" :breakpoint="breakpoint" />
			</div>
		</div>
	</div>
</template>
<script setup>
import { nextTick, onMounted, ref } from "vue";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BuilderBlock from "./BuilderBlock.vue";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import { useDebouncedRefHistory } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { toast } from "frappe-ui";

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
	document.activeElement.blur();
};

document.addEventListener("keydown", (e) => {
	if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
		return;
	}
	if (e.key === "Backspace" && store.builderState.selectedBlock && !e.target.closest(".__builder_component__")) {
		function findBlockAndRemove(blocks, blockId) {
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

onMounted(() => {
	const padding = 100;
	const containerBound = canvasContainer.value.getBoundingClientRect();
	const canvasBound = canvas.value.getBoundingClientRect();
	if (canvasBound.height > containerBound.height) {
		const scale = containerBound.height / (canvasBound.height + padding * 2);
		store.canvas.initialScale = store.canvas.scale = scale;
	}

	nextTick(() => {
		const canvasBound = canvas.value.getBoundingClientRect();
		const scale = store.canvas.scale;
		const diff = containerBound.top - canvasBound.top + padding * scale;
		if (diff !== 0) {
			store.canvas.initialTranslateY = store.canvas.translateY = diff / scale;
		}
		showBlocks.value = true;
	});

	setPanAndZoom(store.canvas, canvas.value, canvasContainer.value);
	const { builderState } = storeToRefs(store);
	const { undo, redo, canUndo, canRedo } = useDebouncedRefHistory(builderState, {
		max: 100,
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
		if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.getAttribute("contenteditable")) {
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

	function findBlock(blocks, blockId) {
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
</script>
