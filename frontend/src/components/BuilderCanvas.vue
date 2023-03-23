<template>
	<div ref="canvasContainer" :style="{
		left: `${store.builderLayout.leftPanelWidth}px`,
		right: `${store.builderLayout.rightPanelWidth}px`
	}">
		<div class="absolute" id="block-draggables"></div>
		<div class="overlay absolute" id="overlay"></div>
		<div class="canvas fixed bg-white rounded-md overflow-hidden" :style="{
			background: store.canvas.background,
			width: store.getActiveBreakpoint() + 'px',
			minHeight: '1400px',
			height: 'fit-content',
			transform: `scale(${store.canvas.scale}) translate(${store.canvas.translateX}px, ${store.canvas.translateY}px)`,
		}" ref="canvas">
			<BuilderBlock :element-properties="store.builderState.blocks[0]" v-if="showBlocks"></BuilderBlock>
		</div>
	</div>
</template>
<script setup>
import { nextTick, onMounted, ref } from "vue";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BuilderBlock from "./BuilderBlock.vue";
import { useDebouncedRefHistory, useRefHistory } from '@vueuse/core';
import { storeToRefs } from "pinia";
import { toast } from 'frappe-ui'

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);
const showBlocks = ref(false);

function getPageData() {
	return store.builderState.blocks;
}

function getBlocks(element) {
	const blocks = [];
	element.childNodes.forEach((node) => {

		if (node.nodeType === Node.ELEMENT_NODE) {
			blocks.push(getBlockData(node));
		} else if (node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()) {
			blocks.push({
				node_type: "Text",
				node_value: node.nodeValue,
			});
		}
	});
	return blocks;
}

function getAttributes(block) {
	const attributes = {};
	const skippedAttributes = {};
	const attributesToSkip = ["contenteditable", "draggable", "style"];

	for (let i = 0; i < block.attributes.length; i += 1) {
		if (attributesToSkip.includes(block.attributes[i].name)) {
			skippedAttributes[block.attributes[i].name] = block.attributes[i].value;
		} else {
			attributes[block.attributes[i].name] = block.attributes[i].value;
		}
	}
	return { attributes, skippedAttributes };
}

function getBlockData(node) {
	const { attributes, skippedAttributes } = getAttributes(node);
	return {
		element: node.tagName.toLowerCase(),
		attributes,
		skippedAttributes,
		styles: node.getAttribute("style"),
		children: getBlocks(node),
	}
}

store.getPageData = getPageData;
store.getBlockData = getBlockData;

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
			if (blockId === 'root') {
				toast({
					title: 'Warning',
					text: 'Cannot Delete Root Block',
					icon: 'alert-circle',
					iconClasses: 'text-yellow-500',
				})
				return false;
			}
			blocks.forEach((block, i) => {
				if (block.blockId === blockId) {
					blocks.splice(i, 1);
					return true;
				} else if (block.children) {
					return findBlockAndRemove(block.children, blockId);
				}
			})
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
		const scale = (containerBound.height) / (canvasBound.height + (padding * 2));
		store.canvas.initialScale = store.canvas.scale = scale;
	}

	nextTick(() => {
		const canvasBound = canvas.value.getBoundingClientRect();
		const scale = store.canvas.scale;
		const diff = (containerBound.top - canvasBound.top + (padding * scale));
		if (diff !== 0) {
			store.canvas.initialTranslateY = store.canvas.translateY = (diff / scale);
		}
		showBlocks.value = true;
	})

	setPanAndZoom(store.canvas, canvas.value, canvasContainer.value);
	const { builderState } = storeToRefs(store);
	const { undo, redo, canUndo, canRedo } = useDebouncedRefHistory(builderState, {
		max: 100,
		deep: true,
		clone: (obj) => {
			let newObj = Object.assign({}, obj);
			newObj.blocks = obj.blocks.map((val) => store.getBlockCopy(val, true));
			if (obj.selectedBlock) {
				newObj.selectedBlock = newObj.blocks.find(d => d.blockId === obj.selectedBlock.blockId);
			};
			return newObj;
		},
		debounce: 200,
	});
	document.addEventListener("keydown", (e) => {
		if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
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
});
</script>
