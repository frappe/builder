<template>
	{{ elementProperties.node_type === 'Text' ? elementProperties.node_value : '' }}
	<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
		class="relative __builder_component__" @click.exact.stop="selectComponent($event, elementProperties)"
		@dblclick.stop v-bind="{ ...elementProperties.attributes, ...elementProperties.skippedAttributes }"
		:style="styles" ref="component">
		{{ elementProperties.innerText }}
		<BuilderBlock :element-properties="element" v-for="element in elementProperties.children"></BuilderBlock>
	</component>
	<teleport to="#draggables" v-if="elementProperties.element === 'section'">
		<BlockDraggables v-if="store.selectedBlocks.includes(elementProperties)" :element-properties="elementProperties"
			v-bind="{ ...$attrs }"></BlockDraggables>
	</teleport>
	<teleport to='#overlay' v-if="elementProperties.node_type !== 'Text'">
		<BlockEditor v-if="store.selectedBlocks.includes(elementProperties)"
			:movable="elementProperties.element === 'span'" :roundable="elementProperties.element === 'section'"
			:resizableX="true" :resizableY="elementProperties.element !== 'img'" :selected="true" :resizable="true">
		</BlockEditor>
	</teleport>
</template>
<script setup>
import { onMounted, ref, reactive } from "vue";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import BlockDraggables from "./BlockDraggables.vue";

const component = ref(null);
const store = useStore();
const props = defineProps(["element-properties"]);
const styles = reactive(props.elementProperties.styles);

onMounted(() => {
	if (props.elementProperties.node_type === "Text") {
		return;
	}
	if (!props.elementProperties.id) {
		props.elementProperties.id = store.generateId();
	}
	selectComponent(null, props.elementProperties);
});

const selectComponent = (e, elementProperties) => {
	// store.selectedComponent = e.target.closest(".__builder_component__");
	// store.selectedComponent.element_id = elementProperties.id;
	store.selectedBlocks = [elementProperties];
};

</script>
