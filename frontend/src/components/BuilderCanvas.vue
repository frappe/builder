<template>
	<div ref="canvasContainer">
		<div class="overlay absolute" id="overlay"></div>
		<div class="absolute" id="draggables"></div>
		<div class="canvas absolute min-h-full h-fit bg-white rounded-md overflow-hidden"
			:style="'width: ' + store.getActiveBreakpoint() + 'px;'" ref="canvas">
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

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);

function getPageData() {
	let blockContainer = canvas.value.querySelector(".block-container");
	// return getBlocks(blockContainer);
	return store.blocks;
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
	store.selectedBlock = null;
	store.selectedBlocks = [];
	document.activeElement.blur();
};

document.addEventListener("keydown", (e) => {
	if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
		return;
	}
	if (e.key === "Backspace" && store.selectedBlock && !e.target.closest(".__builder_component__")) {
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
		find_block_and_remove(store.blocks, store.selectedBlock.blockId);
		clearSelectedComponent();
	}

	if (e.key === "Escape") {
		clearSelectedComponent();
	}
});

onMounted(() => {
	const padding = 40;
	const containerBound = canvasContainer.value.getBoundingClientRect();
	const canvasBound = canvas.value.getBoundingClientRect();
	if (canvasBound.width > containerBound.width) {
		const scale = (containerBound.width) / (canvasBound.width + (padding * 2));
		canvas.value.previousScale = scale;
	}
	const diff = (containerBound.top - canvasBound.top);
	if (diff !== 0) {
		canvas.value.previousY = diff - padding / 2;
	}
	canvas.value.style.transform = `translate(${canvas.value.previousX || 0}px, ${canvas.value.previousY || 0}px) scale(${canvas.value.previousScale})`;
	setPanAndZoom(canvas.value);
});
</script>
