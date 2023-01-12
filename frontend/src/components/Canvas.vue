<template>
	<div class="canvas-container w-3/4 h-[calc(100vh-4rem)] p-10 flex justify-center overflow-hidden"
		ref="canvas_container">
		<div class="canvas h-full flex-col flex page bg-white rounded-md overflow-hidden"
			:style="'width: ' + store.get_active_breakpoint() + 'px;'" ref="canvas" >
			<draggable :list="store.blocks" :group="{ name: 'blocks' }" item-key="id"
				class="w-full h-full flex-col flex block-container">
				<template #item="{ element }">
					<Editable :element-properties="element"></Editable>
				</template>
			</draggable>
		</div>
	</div>
</template>
<script setup>
import { onMounted, ref} from 'vue';
import draggable from 'vuedraggable';
import { useStore } from "../store";
import { set_pan_and_zoom } from '../utils/panandzoom.js';
import Editable from '../block_editors/Editable.vue';

let store = useStore();
function get_page_data() {
	let blocks = [];
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
	// bhai bhai
	canvas.value.getElementsByClassName("block-container")[0].children.forEach(child => {
		const block = child.getElementsByClassName("component")[0]
		const { attributes, skipped_attributes } = get_attributes(block);
		blocks.push({
			"element": block.tagName.toLowerCase(),
			attributes,
			skipped_attributes,
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