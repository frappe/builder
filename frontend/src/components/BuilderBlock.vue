<template>
	{{ elementProperties.node_type === 'Text' ? elementProperties.node_value : '' }}
	<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
		class="relative __builder_component__" @click.exact.stop="selectComponent($event, elementProperties)"
		@dblclick.stop v-bind="{ ...elementProperties.attributes, ...elementProperties.skippedAttributes, ...$attrs }"
		:style="styles"
		:class="elementProperties.classes" ref="component">
		{{ elementProperties.innerText }}
		<BuilderBlock :element-properties="element" v-for="element in elementProperties.children"></BuilderBlock>
	</component>
	<teleport to="#draggables" v-if="elementProperties.element === 'section'">
		<BlockDraggables v-if="store.selectedBlocks.includes(elementProperties)" :element-properties="elementProperties"
			v-bind="{ ...$attrs }"></BlockDraggables>
	</teleport>
	<teleport to='#overlay' v-if="elementProperties.node_type !== 'Text'">
		<BlockEditor v-if="store.selectedBlocks.includes(elementProperties)"
			:roundable="elementProperties.element === 'section'"
			:resizableX="true" :resizableY="elementProperties.element !== 'img'" :selected="true" :resizable="true" :element-properties="elementProperties">
		</BlockEditor>
	</teleport>
</template>
<script setup>
import { onMounted, ref, computed } from "vue";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import BlockDraggables from "./BlockDraggables.vue";

const component = ref(null);
const store = useStore();
const props = defineProps(["element-properties"]);

onMounted(() => {
	if (props.elementProperties.node_type === "Text") {
		return;
	}
	selectComponent(null, props.elementProperties);
});

const styles = computed(() => {
	let styleObj = props.elementProperties.styles;
	if (store.activeBreakpoint === 'mobile') {
		styleObj = {...styleObj, ...props.elementProperties.mobileStyles}
	} else if (store.activeBreakpoint === 'tablet') {
		styleObj = {...styleObj, ...props.elementProperties.tabletStyles}
	}
	return styleObj;
})

const selectComponent = (e, elementProperties) => {
	store.selectedBlock = elementProperties;
	store.selectedBlocks = [elementProperties];
};
</script>
