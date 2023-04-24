<template>
	<draggable
		:list="block.children"
		:sort="true"
		:disabled="preview"
		:group="{ name: 'blocks' }"
		item-key="blockId"
		:tag="block.getTag()"
		@click.stop="selectBlock($event, block)"
		@dblclick.stop
		@mouseover.stop="
			store.hoveredBlock = block.blockId;
			store.hoveredBreakpoint = breakpoint
		"
		@mouseleave.stop="store.hoveredBlock = null"
		@blur="block.innerText = $event.target.innerText"
		:component-data="{
			...block.attributes,
			...$attrs,
			...{
				'data-block-id': block.blockId,
				contenteditable: block.isText() && isSelected,
				class: ['__builder_component__', 'outline-none', 'select-none', ...(block.classes || [])],
				style: { ...styles, ...block.editorStyles },
			},
		}"
		ref="component">
		<template #header>
			{{ block.innerText }}
		</template>
		<template #item="{ element }">
			<BuilderBlock :block="element" :breakpoint="breakpoint" />
		</template>
	</draggable>
	<teleport to="#overlay">
		<BlockEditor
			v-if="(
				(isSelected && breakpoint === store.builderState.activeBreakpoint) ||
				(store.hoveredBlock === block.blockId && store.hoveredBreakpoint === breakpoint)
			) && !preview"
			:resizable-x="!block.isRoot()"
			:resizable-y="!block.isImage() && !block.isRoot()"
			:selected="isSelected"
			:resizable="!block.isRoot()"
			:block="block"
			:breakpoint="breakpoint"
			:target="component.targetDomElement" />
	</teleport>
</template>
<script setup lang="ts">
import { onMounted, ref, computed, Ref } from "vue";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import draggable from "vuedraggable";
import Block from "@/utils/block";

// TODO: Find better way to set type for draggable
// sortable object for draggable has targetDomElement
const component = ref(null) as unknown as Ref<{ targetDomElement: HTMLElement }>;
const store = useStore();
const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
	breakpoint: {
		type: String,
		default: "desktop",
	},
	preview: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["renderComplete"]);


onMounted(() => {
	selectBlock(null, props.block);
	let targetElement = component.value.targetDomElement;
	if (props.block.isText()) {
		targetElement.addEventListener("keydown", (e: KeyboardEvent) => {
			if (e.key === "b" && e.metaKey) {
				e.preventDefault();
				props.block.setStyle("fontWeight", "bold");
			}
		});
	}
	emit("renderComplete", targetElement);
});

const styles = computed(() => {
	let styleObj = props.block.styles;
	if (props.breakpoint === "mobile") {
		styleObj = { ...styleObj, ...props.block.mobileStyles };
	} else if (props.breakpoint === "tablet") {
		styleObj = { ...styleObj, ...props.block.tabletStyles };
	}
	return styleObj;
});

const isSelected = computed(() => {
	return (
		store.builderState.selectedBlock === props.block ||
		store.builderState.selectedBlocks.includes(props.block)
	);
});

const selectBlock = (e: MouseEvent | null, block: Block) => {
	if (e) e.preventDefault();
	store.builderState.selectedBlock = block;
	store.builderState.activeBreakpoint = props.breakpoint;
	if (e && e.metaKey) {
		if (!store.builderState.selectedBlocks.length) {
			store.builderState.selectedBlocks.push(store.builderState.selectedBlock);
		}
		store.builderState.selectedBlocks.push(block);
	}
};
</script>
