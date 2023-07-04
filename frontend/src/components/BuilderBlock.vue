<template>
	<draggable
		:list="block.children"
		:sort="true"
		:disabled="preview"
		:group="{ name: 'blocks' }"
		item-key="blockId"
		:tag="block.getTag()"
		@click="handleClick"
		@dblclick.stop="handleDoubleClick"
		@contextmenu.prevent.stop="triggerContextMenu($event)"
		@mouseover="handleMouseOver"
		@mouseleave="handleMouseLeave"
		@blur="block.innerText = $event.target.innerText"
		:component-data="{
			...block.attributes,
			...$attrs,
			...{
				'data-block-id': block.blockId,
				contenteditable: (block.isText() || block.isButton()) && block.isSelected() && isEditable,
				class: [
					$attrs.class,
					'__builder_component__',
					'outline-none',
					'select-none',
					...(block.classes || []),
				],
				style: { ...styles, ...block.editorStyles },
			},
		}"
		:class="{
			'pointer-events-none': props.isChildOfComponent,
		}"
		ref="component">
		<template #header>
			{{ block.innerText }}
		</template>
		<template #item="{ element }">
			<BuilderBlock
				:block="element"
				:breakpoint="breakpoint"
				:preview="preview"
				:isChildOfComponent="block.isComponent" />
		</template>
	</draggable>
	<teleport to="#overlay" v-if="store.overlayElement && !preview">
		<BlockEditor
			v-if="component && store.builderState.mode !== 'container' && component.targetDomElement"
			v-show="
				((block.isSelected() && breakpoint === store.builderState.activeBreakpoint) ||
					(block.isHovered() && store.hoveredBreakpoint === breakpoint)) &&
				!store.canvas.scaling &&
				!store.canvas.panning
			"
			:resizable-x="!block.isRoot()"
			:resizable-y="!block.isImage() && !block.isRoot()"
			:resizable="!block.isRoot()"
			:block="block"
			:breakpoint="breakpoint"
			:editable="isEditable"
			:target="component.targetDomElement" />
	</teleport>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { setFont } from "@/utils/fontManager";
import { Ref, computed, nextTick, onMounted, ref, watchEffect } from "vue";
import draggable from "vuedraggable";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";

// TODO: Find better way to set type for draggable
// sortable object for draggable has targetDomElement
const component = ref(null) as unknown as Ref<{ targetDomElement: HTMLElement }>;
const store = useStore();
const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
	isChildOfComponent: {
		type: Boolean,
		default: false,
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
	setFont(props.block.getStyle("fontFamily") as string);
	let targetElement = component.value.targetDomElement;
	if (props.block.isText()) {
		targetElement.addEventListener("keydown", (e: KeyboardEvent) => {
			if (e.key === "b" && e.metaKey) {
				e.preventDefault();
				props.block.setStyle("fontWeight", "700");
			}
		});
	}
	nextTick(() => {
		emit("renderComplete", targetElement);
	});
});

const styles = computed(() => {
	let styleObj = props.block.baseStyles;
	if (props.breakpoint === "mobile") {
		styleObj = { ...styleObj, ...props.block.mobileStyles };
	} else if (props.breakpoint === "tablet") {
		styleObj = { ...styleObj, ...props.block.tabletStyles };
	}
	styleObj = { ...styleObj, ...props.block.rawStyles };
	return styleObj;
});

const isEditable = computed(() => {
	return (
		store.builderState.editableBlock === props.block && !(props.block.isComponent || props.isChildOfComponent)
	);
});

const selectBlock = (e: MouseEvent | null, block: Block) => {
	if (
		store.builderState.editableBlock === props.block ||
		store.builderState.mode !== "select" ||
		props.preview
	) {
		return;
	}
	if (e) e.preventDefault();
	store.builderState.selectedBlock = block;
	store.builderState.editableBlock = null;
	store.builderState.activeBreakpoint = props.breakpoint;
	if (e && e.metaKey) {
		if (!store.builderState.selectedBlocks.length) {
			store.builderState.selectedBlocks.push(store.builderState.selectedBlock);
		}
		store.builderState.selectedBlocks.push(block);
	}

	if (!props.preview && props.block.isSelected()) {
		store.sidebarActiveTab = "Layers";
	}
};

const triggerContextMenu = (e: MouseEvent) => {
	selectBlock(e, props.block);
	nextTick(() => {
		let element = document.elementFromPoint(e.x, e.y) as HTMLElement;
		if (element === component.value.targetDomElement) return;
		element.dispatchEvent(
			new MouseEvent("contextmenu", {
				bubbles: true,
				cancelable: true,
				clientX: e.clientX,
				clientY: e.clientY,
			})
		);
	});
};

const handleClick = (e: MouseEvent) => {
	if (!props.isChildOfComponent) {
		e.stopPropagation();
		selectBlock(e, props.block);
	}
};

const handleDoubleClick = () => {
	store.builderState.editableBlock = null;
	if (props.block.isText()) {
		store.builderState.editableBlock = props.block;
	}
};

const handleMouseOver = (e: MouseEvent) => {
	if (!props.isChildOfComponent) {
		e.stopPropagation();
		store.hoveredBlock = props.block.blockId;
		store.hoveredBreakpoint = props.breakpoint;
	}
};

const handleMouseLeave = (e: MouseEvent) => {
	console.log(props.block.blockId, "leave");
	if (!props.isChildOfComponent) {
		if (store.hoveredBlock === props.block.blockId) {
			e.stopPropagation();
			store.hoveredBlock = null;
		}
	}
};

watchEffect(() => {
	if (isEditable.value) {
		nextTick(() => {
			const range = document.createRange();
			range.selectNodeContents(component.value.targetDomElement);
			const selection = window.getSelection();
			selection?.removeAllRanges();
			selection?.addRange(range);
		});
	}
});
</script>
