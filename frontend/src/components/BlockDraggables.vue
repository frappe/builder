<template>
	<div ref="draggableContainer" class="fixed z-20 pointer-events-none">
		<draggable :list="elementProperties.children"
			:group="{ name: 'blocks' }" item-key="id" class="w-full h-full flex-col flex pointer-events-auto justify-center items-center block-draggable" @click="handleClick">
			<template #item="{ element }">
				<!--  -->
			</template>
		</draggable>
	</div>
</template>
<script setup>
import { getCurrentInstance, onMounted, ref } from "vue";
import draggable from "vuedraggable";
import trackTarget from "../utils/trackTarget";

const props = defineProps(["element-properties"]);
const draggableContainer = ref(null);

let currentInstance = null;
let target = null;
onMounted(() => {
	currentInstance = getCurrentInstance();
	const draggableWrapper = draggableContainer.value;
	target = currentInstance.parent.refs.component;
	trackTarget(target, draggableWrapper, 20);
});

const handleClick = (ev) => {
	// click on target instead of draggable box
	ev.target.classList.add("pointer-events-none");
	ev.target.classList.remove("pointer-events-auto");
	let target = document.elementFromPoint(ev.x, ev.y);
	if (target) {
		target.click();
	}
}
</script>