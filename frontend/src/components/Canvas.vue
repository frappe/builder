<template>
	<div class="canvas-container w-3/4 h-[calc(100vh-4rem)] p-10 flex justify-center overflow-hidden" ref="canvas_container">
		<div class="canvas h-full flex-col flex page bg-white rounded-md overflow-hidden" :style="'width: ' + store.get_active_breakpoint() + 'px;'"
			ref="canvas">
			<draggable
				:list="store.blocks"
				:group="{ name: 'widgets' }"
				item-key="id"
				class="w-full h-full flex-col flex block-container"
			>
				<template #item="{ element }">
					<Editable :element-properties="element"></Editable>
				</template>
			</draggable>
		</div>
	</div>
</template>
<script setup>
import { onMounted, ref, provide } from 'vue';
import draggable from 'vuedraggable';
import { useStore } from "../store";
import { set_pan_and_zoom } from '../utils/panandzoom.js';
import Editable from '../block_editors/Editable.vue';

let store = useStore();
function get_page_data() {
	let blocks = [];
	function get_attributes(block) {
		let attributes = {};
		for (let i = 0; i < block.attributes.length; i++) {
			if (["style", "contenteditable", "draggable"].includes(block.attributes[i].name)) {
				continue;
			}
			attributes[block.attributes[i].name] = block.attributes[i].value;
		}
		return attributes;
	}
	// bhai bhai
	canvas.value.getElementsByClassName("block-container")[0].children.forEach(child => {
		const block = child.getElementsByClassName("component")[0]
		blocks.push({
			"element": block.tagName.toLowerCase(),
			"attributes": get_attributes(block),
			"styles": block.getAttribute("style"),
			"innerText": block.innerText
		})
	});
	return blocks;
}

store.get_page_data = get_page_data;

const canvas_container = ref(null);
const canvas = ref(null);

onMounted(() => {
	set_pan_and_zoom(canvas.value)
})

</script>