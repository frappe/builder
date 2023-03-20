<template>
	<div ref="canvasContainer" :style="{
		left: `${store.builderLayout.leftPanelWidth}px`,
		right: `${store.builderLayout.rightPanelWidth}px`
	}">
		<div class="absolute" id="draggables"></div>
		<div class="overlay absolute" id="overlay"></div>
		<div class="canvas absolute min-h-full h-fit bg-white rounded-md overflow-hidden"
			:style="{
				width: store.getActiveBreakpoint() + 'px',
				transform: `scale(${store.canvas.scale}) translate(${store.canvas.translateX}px, ${store.canvas.translateY}px)`,
			}" ref="canvas">
			<draggable :list="store.blocks" :group="{ name: 'blocks' }" item-key="id"
				class="h-full w-auto flex-col block-container min-h-[300px]">
				<template #item="{ element }">
					<BuilderBlock :element-properties="element"></BuilderBlock>
				</template>
			</draggable>
		</div>
	</div>
</template>
<script setup>
import { onMounted, ref } from "vue";
import draggable from "vuedraggable";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BuilderBlock from "./BuilderBlock.vue";
import { useDebouncedRefHistory, useRefHistory } from '@vueuse/core';
import { storeToRefs } from "pinia";

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);

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
		function find_block_and_remove(blocks, block_id) {
			blocks.forEach((block, i) => {
				if (block.blockId === block_id) {
					blocks.splice(i, 1);
					return true;
				} else if (block.children) {
					return find_block_and_remove(block.children, block_id);
				}
			})
		}
		find_block_and_remove(store.builderState.blocks, store.builderState.selectedBlock.blockId);
		clearSelectedComponent();
	}

	if (e.key === "Escape") {
		clearSelectedComponent();
	}
});

onMounted(() => {

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
