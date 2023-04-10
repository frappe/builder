<template>
	<draggable
		:list="elementProperties.children"
		:sort="true"
		:disabled="preview"
		:group="{ name: 'blocks' }"
		item-key="blockId"
		:tag="elementProperties.getTag()"
		@click.stop="selectBlock($event, elementProperties)"
		@dblclick.stop
		@mouseover.stop="store.hoveredBlock = elementProperties.blockId"
		@mouseleave.stop="store.hoveredBlock = null"
		@blur="elementProperties.innerText = $event.target.innerText"
		:component-data="{
			...elementProperties.attributes,
			...$attrs,
			...{
				'data-block-id': elementProperties.blockId,
				contenteditable: elementProperties.isText() && isSelected,
				class: ['__builder_component__', 'outline-none', 'select-none', ...(elementProperties.classes || [])],
				style: { ...styles, ...elementProperties.editorStyles },
			},
		}"
		ref="component">
		<template #header>
			{{ elementProperties.innerText }}
		</template>
		<template #item="{ element }">
			<BuilderBlock :element-properties="element" />
		</template>
	</draggable>
	<teleport to="#overlay">
		<BlockEditor
			v-if="(isSelected || store.hoveredBlock === elementProperties.blockId) && !preview"
			:roundable="elementProperties.isContainer() || elementProperties.isDiv() || elementProperties.isImage()"
			:resizable-x="!elementProperties.isRoot()"
			:resizable-y="!elementProperties.isImage() && !elementProperties.isRoot()"
			:selected="isSelected"
			:resizable="!elementProperties.isRoot()"
			:element-properties="elementProperties" />
	</teleport>
</template>
<script setup>
import { onMounted, ref, computed } from "vue";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import draggable from "vuedraggable";

const component = ref(null);
const store = useStore();
const props = defineProps(["element-properties", "preview"]);
const emit = defineEmits(["renderComplete"]);

onMounted(() => {
	selectBlock(null, props.elementProperties);
	let targetElement = component.value.targetDomElement;
	if (props.elementProperties.isText()) {
		targetElement.addEventListener("keydown", (e) => {
			if (e.key === "b" && e.metaKey) {
				e.preventDefault();
				props.elementProperties.setStyle("fontWeight", "bold");
			}
		});
	}
	emit("renderComplete", targetElement);
});

const styles = computed(() => {
	let styleObj = props.elementProperties.styles;
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = { ...styleObj, ...props.elementProperties.mobileStyles };
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = { ...styleObj, ...props.elementProperties.tabletStyles };
	}
	return styleObj;
});

const isSelected = computed(() => {
	return (
		store.builderState.selectedBlock === props.elementProperties ||
		store.builderState.selectedBlocks.includes(props.elementProperties)
	);
});

const selectBlock = (e, block) => {
	if (e) e.preventDefault();
	store.builderState.selectedBlock = block;
	if (e && e.metaKey) {
		if (!store.builderState.selectedBlocks.length) {
			store.builderState.selectedBlocks.push(store.builderState.selectedBlock);
		}
		store.builderState.selectedBlocks.push(block);
	}
};
</script>
