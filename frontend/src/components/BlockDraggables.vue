<template>
	<div ref="draggableContainer" class="fixed z-20 pointer-events-none p-2">
		<draggable :list="elementProperties.children"
			:group="{ name: 'blocks' }" item-key="id" class="w-full h-full flex-col flex block-container">
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
	trackTarget(target, draggableWrapper);
});
</script>