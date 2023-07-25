<template>
	<component
		:is="getComponentName(block)"
		@click="handleClick"
		@dblclick="handleDoubleClick"
		@contextmenu="triggerContextMenu($event)"
		@mouseover="handleMouseOver"
		@mouseleave="handleMouseLeave"
		:data-block-id="block.blockId"
		:block="block.isText() || block.isHTML() ? block : null"
		:class="[$attrs.class, '__builder_component__', 'outline-none', 'select-none', ...(block.classes || [])]"
		v-bind="{ ...block.attributes, ...$attrs }"
		:style="{ ...styles, ...block.getEditorStyles() }"
		ref="component">
		<BuilderBlock
			:block="child"
			:breakpoint="breakpoint"
			:preview="preview"
			:isChildOfComponent="child.isComponent"
			v-for="child in block.children" />
	</component>
	<teleport to="#overlay" v-if="store.overlayElement && !preview && canvasProps">
		<BlockEditor
			v-if="loadEditor"
			v-show="!canvasProps.scaling && !canvasProps.panning"
			:block="block"
			:breakpoint="breakpoint"
			:editable="isEditable"
			:target="(target as HTMLElement)" />
	</teleport>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { setFont } from "@/utils/fontManager";
import { computed, inject, nextTick, onMounted, ref } from "vue";

import getBlockTemplate from "@/utils/blockTemplate";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import BlockHTML from "./BlockHTML.vue";
import TextBlock from "./TextBlock.vue";

const component = ref<HTMLElement | InstanceType<typeof TextBlock> | null>(null);
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

const getComponentName = (block: Block) => {
	if (block.isText()) {
		return TextBlock;
	} else if (block.isHTML()) {
		return BlockHTML;
	} else {
		return block.getTag();
	}
};

const canvasProps = !props.preview ? (inject("canvasProps") as CanvasProps) : null;

const target = computed(() => {
	if (!component.value) return null;
	if (component.value instanceof HTMLElement) {
		return component.value;
	} else {
		return component.value.component;
	}
});

const loadEditor = computed(() => {
	return (
		target.value &&
		store.builderState.mode !== "container" &&
		((props.block.isSelected() && props.breakpoint === store.builderState.activeBreakpoint) ||
			(props.block.isHovered() && store.hoveredBreakpoint === props.breakpoint))
	);
});

onMounted(async () => {
	selectBlock(null);
	setFont(props.block.getStyle("fontFamily") as string);
	await nextTick();
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
		store.builderState.editableBlock === props.block &&
		!(props.block.isComponent || props.isChildOfComponent) &&
		store.builderState.activeBreakpoint === props.breakpoint // to ensure it is right block and not on different breakpoint
	);
});

const selectBlock = (e: MouseEvent | null) => {
	if (
		store.builderState.editableBlock === props.block ||
		store.builderState.mode !== "select" ||
		props.preview
	) {
		return;
	}
	store.selectBlock(props.block, e);
	store.builderState.activeBreakpoint = props.breakpoint;

	if (!props.preview) {
		store.sidebarActiveTab = "Layers";
	}
};

const triggerContextMenu = (e: MouseEvent) => {
	if (props.block.isRoot()) return;
	e.stopPropagation();
	e.preventDefault();
	selectBlock(e);
	nextTick(() => {
		let element = document.elementFromPoint(e.x, e.y) as HTMLElement;
		if (element === target.value) return;
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
	if (isEditable.value) return;
	if (!props.isChildOfComponent) {
		selectBlock(e);
		e.stopPropagation();
		e.preventDefault();
	}
};

const handleDoubleClick = (e: MouseEvent) => {
	if (isEditable.value) return;
	store.builderState.editableBlock = null;
	if (props.block.isText()) {
		store.builderState.editableBlock = props.block;
		e.stopPropagation();
	}
	if (props.block.isComponent) {
		store.editingComponent = props.block;
		e.stopPropagation();
	}

	// dblclick on container adds text block or selects text block if only one child
	if (props.block.isContainer()) {
		if (props.block.children.length === 0) {
			const child = getBlockTemplate("text");
			const childBlock = props.block.addChild(child);
			childBlock.makeBlockEditable();
			e.stopPropagation();
		} else if (props.block.children.length === 1 && props.block.children[0].isText()) {
			const child = props.block.children[0];
			child.makeBlockEditable();
			e.stopPropagation();
		}
	}
};

const handleMouseOver = (e: MouseEvent) => {
	if (!props.isChildOfComponent) {
		store.hoveredBlock = props.block.blockId;
		store.hoveredBreakpoint = props.breakpoint;
		e.stopPropagation();
	}
};

const handleMouseLeave = (e: MouseEvent) => {
	if (!props.isChildOfComponent) {
		if (store.hoveredBlock === props.block.blockId) {
			store.hoveredBlock = null;
			e.stopPropagation();
		}
	}
};
</script>
