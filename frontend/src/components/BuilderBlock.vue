<template>
	{{ elementProperties.node_type === 'Text' ? elementProperties.node_value : '' }}
	<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
		class="relative __builder_component__" @click.stop="selectBlock($event, elementProperties)"
		@dblclick.stop v-bind="{ ...elementProperties.attributes, ...elementProperties.skippedAttributes, ...$attrs }"
		:style="styles"
		:contenteditable="elementProperties.isText()"
		:class="elementProperties.classes" ref="component">
		{{ elementProperties.innerText }}
		<BuilderBlock :element-properties="element" v-for="element in elementProperties.children"></BuilderBlock>
	</component>
	<teleport to="#draggables" v-if="elementProperties.element === 'section'">
		<BlockDraggables v-if="isSelected" :element-properties="elementProperties"
			v-bind="{ ...$attrs }"></BlockDraggables>
	</teleport>
	<teleport to='#overlay' v-if="elementProperties.node_type !== 'Text'">
		<BlockEditor v-if="isSelected || elementProperties.hover"
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
	selectBlock(null, props.elementProperties);
	if (props.elementProperties.isText()) {
		component.value.addEventListener("keydown", (e) => {
			if (e.key === "b" && e.metaKey) {
				console.log('bold');
				e.preventDefault();
				props.elementProperties.setStyle("fontWeight", "bold");
			}
		});
	}
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

const isSelected = computed(() => {
	return store.selectedBlock === props.elementProperties || store.selectedBlocks.includes(props.elementProperties);
});

const selectBlock = (e, block) => {
	store.selectedBlock = block;
	if (e && e.metaKey) {
		if (!store.selectedBlocks.length) {
			store.selectedBlocks.push(store.selectedBlock);
		}
		store.selectedBlocks.push(block);
	}
};
</script>
