<template>
	<component :is="elementProperties.getTag()"
		class="relative __builder_component__ outline-none" @click.stop="selectBlock($event, elementProperties)"
		@dblclick.stop v-bind="{ ...elementProperties.attributes, ...elementProperties.skippedAttributes, ...$attrs }"
		:style="{ ...styles, ...elementProperties.editorStyles }"
		:contenteditable="elementProperties.isText() && isSelected"
		:class="elementProperties.classes"
		@mouseover.stop="store.hoveredBlock = elementProperties.blockId"
		@mouseleave.stop="store.hoveredBlock = null"
		@blur="elementProperties.innerText = $event.target.innerText"
		ref="component">
		{{ elementProperties.innerText }}
		<BuilderBlock :element-properties="element" v-for="element in elementProperties.children"></BuilderBlock>
	</component>
	<teleport to="#block-draggables" v-if="elementProperties.isContainer() || elementProperties.isRoot()">
		<BlockDraggables v-if="isSelected || elementProperties.isRoot()" :element-properties="elementProperties"
			v-bind="{ ...$attrs }"></BlockDraggables>
	</teleport>
	<teleport to='#overlay'>
		<BlockEditor v-if="isSelected || store.hoveredBlock === elementProperties.blockId"
			:roundable="elementProperties.isContainer()"
			:resizableX="!elementProperties.isRoot()" :resizableY="!elementProperties.isImage() && !elementProperties.isRoot()" :selected="isSelected" :resizable="!elementProperties.isRoot()" :element-properties="elementProperties">
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
	props.elementProperties.component = component.value;
	selectBlock(null, props.elementProperties);
	if (props.elementProperties.isText()) {
		component.value.addEventListener("keydown", (e) => {
			if (e.key === "b" && e.metaKey) {
				e.preventDefault();
				props.elementProperties.setStyle("fontWeight", "bold");
			}
		});
	}
});

const styles = computed(() => {
	let styleObj = props.elementProperties.styles;
	if (store.builderState.activeBreakpoint === 'mobile') {
		styleObj = {...styleObj, ...props.elementProperties.mobileStyles}
	} else if (store.builderState.activeBreakpoint === 'tablet') {
		styleObj = {...styleObj, ...props.elementProperties.tabletStyles}
	}
	return styleObj;
})

const isSelected = computed(() => {
	return store.builderState.selectedBlock === props.elementProperties || store.builderState.selectedBlocks.includes(props.elementProperties);
});

const selectBlock = (e, block) => {
	store.sidebarActiveTab = "Layers";
	store.builderState.selectedBlock = block;
	if (e && e.metaKey) {
		if (!store.builderState.selectedBlocks.length) {
			store.builderState.selectedBlocks.push(store.builderState.selectedBlock);
		}
		store.builderState.selectedBlocks.push(block);
	}
};
</script>
