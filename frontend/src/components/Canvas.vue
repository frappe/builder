<template>
	<div class="canvas-container w-3/4 h-[calc(100vh-3.5rem)] p-10 flex justify-center overflow-hidden"
		ref="canvas_container" @click="clear_selected_component">
		<div class="canvas min-h-full h-[calc(fit-content+2rem)] flex-col flex page bg-white rounded-md overflow-hidden"
			:style="'width: ' + store.get_active_breakpoint() + 'px;'" ref="canvas" >
			<draggable :list="store.blocks" :group="{ name: 'blocks' }" item-key="id"
				class="w-full h-full flex-col flex block-container min-h-[300px]">
				<template #item="{ element }">
					<Editable :element-properties="element" @drag.start="set_copy_data($event, element, i)" @drag.end="copy"></Editable>
				</template>
			</draggable>
		</div>
	</div>
</template>
<script setup>
import { onMounted, ref} from 'vue';
import draggable from 'vuedraggable';
import { useStore } from "../store";
import { useDebounceFn } from '@vueuse/core';

import { set_pan_and_zoom } from '../utils/panandzoom.js';
import Editable from '../block_editors/Editable.vue';
let store = useStore();

const set_copy_data = useDebounceFn((event, data, i) => {
	if (event.altKey) {
		event.dataTransfer.action = 'copy';
		event.dataTransfer.data_to_copy = JSON.parse(JSON.stringify(data));
	}
})

const copy = useDebounceFn((event) => {
	if (event.dataTransfer.action === 'copy') {
		store.blocks.push(event.dataTransfer.data_to_copy);
	}
})

function get_page_data() {
	function get_attributes(block) {
		const attributes = {};
		const skipped_attributes = {};
		const attributes_to_skip = ["contenteditable", "draggable", "style"];

		for (let i = 0; i < block.attributes.length; i++) {
			if (attributes_to_skip.includes(block.attributes[i].name)) {
				skipped_attributes[block.attributes[i].name] = block.attributes[i].value;
				continue;
			}
			attributes[block.attributes[i].name] = block.attributes[i].value;
		}
		return {attributes, skipped_attributes};
	}

	function get_blocks(element) {
		let blocks = []
		element.childNodes.forEach(node => {
			if (node.nodeType === Node.ELEMENT_NODE) {
				// if (!node.classList.contains("component")) {
				// 	const components = node.getElementsByClassName("component")
				// 	if (components.length) {
				// 		node = components[0];
				// 	} else {
				// 		return;
				// 	}
				// }
				const { attributes, skipped_attributes } = get_attributes(node);
				blocks.push({
					"element": node.tagName.toLowerCase(),
					attributes,
					skipped_attributes,
					"styles": node.getAttribute("style"),
					"children": get_blocks(node),
				})
			} else if (node.nodeType === Node.TEXT_NODE) {
				blocks.push({
					"node_type": "Text",
					"node_value": node.nodeValue,
				})
			}
		})
		return blocks
	}
	return get_blocks(canvas.value.getElementsByClassName("block-container")[0]);
}

store.get_page_data = get_page_data;

const canvas_container = ref(null);
const canvas = ref(null);

onMounted(() => {
	set_pan_and_zoom(canvas.value)
})

const clear_selected_component = () => {
	store.selected_component = null;
}

</script>