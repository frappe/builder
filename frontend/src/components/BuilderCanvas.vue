<template>
	<div
		class="canvas-container w-3/4 h-[calc(100vh-3.5rem)] p-10 flex justify-center overflow-hidden"
		ref="canvasContainer" @click="clearSelectedComponent">
		<div class="overlay absolute" id="overlay"></div>
		<div class="canvas absolute min-h-full h-fit bg-white rounded-md overflow-hidden"
			:style="'width: ' + store.getActiveBreakpoint() + 'px;'" ref="canvas">
			<draggable :list="store.blocks" :group="{ name: 'blocks' }" item-key="id"
				class="h-full w-auto flex-col block-container min-h-[300px] mx">
				<template #item="{ element }">
					<BuilderBlock :element-properties="element" @dragstart="setCopyData($event, element, i)"
						@drag.end="copy"></BuilderBlock>
				</template>
			</draggable>
		</div>
	</div>
</template>
<script setup>
import { useDebounceFn } from "@vueuse/core";
import { onMounted, ref } from "vue";
import draggable from "vuedraggable";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BuilderBlock from "./BuilderBlock.vue";

const store = useStore();

const setCopyData = useDebounceFn((event, data) => {
	if (event.altKey) {
		event.dataTransfer.action = "copy";
		event.dataTransfer.data_to_copy = JSON.parse(JSON.stringify(data));
	}
});
const copy = useDebounceFn((event) => {
	if (event.dataTransfer.action === "copy") {
		store.blocks.push(event.dataTransfer.data_to_copy);
	}
});

const canvasContainer = ref(null);
const canvas = ref(null);

function getPageData() {
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

	function getBlocks(element) {
		const blocks = [];
		element.childNodes.forEach((node) => {
			if (node.nodeType === Node.ELEMENT_NODE) {
				const { attributes, skippedAttributes } = getAttributes(node);
				blocks.push({
					element: node.tagName.toLowerCase(),
					attributes,
					skippedAttributes,
					styles: node.getAttribute("style"),
					children: getBlocks(node),
				});
			} else if (node.nodeType === Node.TEXT_NODE) {
				blocks.push({
					node_type: "Text",
					node_value: node.nodeValue,
				});
			}
		});
		return blocks;
	}
	return getBlocks(canvas.value);
}

store.getPageData = getPageData;

onMounted(() => {
	setPanAndZoom(canvas.value);
});

const clearSelectedComponent = () => {
	store.selectedComponent = null;
};

document.addEventListener("keydown", (e) => {
	if (e.key === "Backspace" && store.selectedComponent && !e.target.closest(".__builder_component__")) {
		store.blocks = store.blocks.filter((block) => block.id !== store.selectedComponent.element_id);
		store.selectedComponent = null;
	}

	if (e.key === "Escape") {
		store.selectedComponent = null;
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
});

</script>
