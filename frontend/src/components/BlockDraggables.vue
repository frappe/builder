<template>
	<div ref="draggableContainer" class="pointer-events-none fixed z-20">
		<draggable
			:list="elementProperties.children"
			:sort="true"
			:group="{ name: 'blocks' }"
			item-key="blockId"
			class="block-draggable pointer-events-none h-full w-full"
			@click="handleClick">
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
};
</script>
