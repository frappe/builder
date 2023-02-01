<template>
	<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
		class="flex items-center justify-center relative __builder_component__ cursor-default"
		@click.exact.stop="selectComponent($event, elementProperties)" @dblclick.stop
		v-bind="{ ...elementProperties.attributes, ...elementProperties.skipped_attributes }"
		:style="elementProperties.styles" ref="component">
		{{ elementProperties.innerText }}
		<BuilderBlock :element-properties="element" v-for="element in elementProperties.blocks"></BuilderBlock>
	</component>
	<teleport to="#draggables" v-if="elementProperties.element === 'section'">
		<BlockDraggables :element-properties="elementProperties"></BlockDraggables>
	</teleport>
	<teleport to='#overlay'>
		<BlockEditor
			:movable="elementProperties.element === 'span'"
			:roundable="elementProperties.element !== 'span'"
			:resizable="true"></BlockEditor>
	</teleport>
</template>
<script setup>
import { onMounted, ref } from "vue";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import BlockDraggables from "./BlockDraggables.vue";

const component = ref(null);
const store = useStore();
const props = defineProps(["element-properties"]);

onMounted(() => {
	store.selectedComponent = component.value;
	store.selectedComponent.element_id = props.elementProperties.id;
});

const selectComponent = (e, elementProperties) => {
	store.selectedComponent = e.target.closest(".__builder_component__");
	store.selectedComponent.element_id = elementProperties.id;
};

</script>
