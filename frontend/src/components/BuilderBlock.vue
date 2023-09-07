<template>
	<component
		:is="getComponentName(block)"
		@click="handleClick"
		@dblclick="handleDoubleClick"
		@contextmenu="triggerContextMenu($event)"
		@mouseover="handleMouseOver"
		@mouseleave="handleMouseLeave"
		:data-block-id="block.blockId"
		:draggable="draggable"
		:class="classes"
		v-bind="attributes"
		:style="styles"
		ref="component">
		<BuilderBlock
			:data="data"
			:block="child"
			:breakpoint="breakpoint"
			:preview="preview"
			:isChildOfComponent="block.isExtendedFromComponent() || isChildOfComponent"
			:key="child.blockId"
			v-for="child in block.getChildren()" />
	</component>
	<teleport to="#overlay" v-if="canvasProps?.overlayElement && !preview && canvasProps">
		<BlockEditor
			ref="editor"
			v-if="loadEditor"
			:block="block"
			:breakpoint="breakpoint"
			:editable="isEditable"
			:target="(target as HTMLElement)" />
	</teleport>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { setFont } from "@/utils/fontManager";
import { computed, inject, nextTick, onMounted, reactive, ref, useAttrs, watchEffect } from "vue";

import getBlockTemplate from "@/utils/blockTemplate";
import { useDraggableBlock } from "@/utils/useDraggableBlock";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import BlockHTML from "./BlockHTML.vue";
import DataLoaderBlock from "./DataLoaderBlock.vue";
import TextBlock from "./TextBlock.vue";

const component = ref<HTMLElement | InstanceType<typeof TextBlock> | null>(null);
const attrs = useAttrs();
const store = useStore();
const editor = ref<InstanceType<typeof BlockEditor> | null>(null);

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
	data: {
		type: Object,
		default: null,
	},
});

const draggable = computed(() => {
	// TODO: enable this
	return !props.block.isRoot() && !props.preview && false;
});

const getComponentName = (block: Block) => {
	if (block.isRepeater()) {
		return DataLoaderBlock;
	}
	if (block.isText() || block.isLink() || block.isButton()) {
		return TextBlock;
	} else if (block.isHTML()) {
		return BlockHTML;
	} else {
		return block.getTag();
	}
};

const classes = computed(() => {
	return [attrs.class, "__builder_component__", "outline-none", "select-none", ...props.block.getClasses()];
});

const attributes = computed(() => {
	const attribs = { ...props.block.getAttributes(), ...attrs } as { [key: string]: any };
	if (
		props.block.isText() ||
		props.block.isHTML() ||
		props.block.isLink() ||
		props.block.isButton() ||
		props.block.isRepeater()
	) {
		attribs.block = props.block;
		attribs.preview = props.preview;
		attribs.breakpoint = props.breakpoint;
		attribs.data = props.data;
	}
	if (props.data) {
		if (props.block.getDataKey("type") === "attribute" && props.data[props.block.getDataKey("key")]) {
			attribs[props.block.getDataKey("property") as string] =
				props.data[props.block.getDataKey("key") as string];
		}
	}
	return attribs;
});

const canvasProps = !props.preview ? (inject("canvasProps") as CanvasProps) : null;

const target = computed(() => {
	if (!component.value) return null;
	if (component.value instanceof HTMLElement) {
		return component.value;
	} else {
		return component.value.component;
	}
});

const styles = computed(() => {
	return { ...props.block.getStyles(props.breakpoint), ...props.block.getEditorStyles() };
});

const loadEditor = computed(() => {
	return (
		!canvasProps?.scaling &&
		!canvasProps?.panning &&
		target.value &&
		props.block.getStyle("display") !== "none" &&
		((props.block.isSelected() && props.breakpoint === store.activeBreakpoint) ||
			(props.block.isHovered() && store.hoveredBreakpoint === props.breakpoint))
	);
});

const emit = defineEmits(["mounted"]);

watchEffect(() => {
	setFont(props.block.getStyle("fontFamily") as string);
});

onMounted(async () => {
	await nextTick();
	emit("mounted", target.value);

	if (draggable.value) {
		useDraggableBlock(
			props.block,
			component.value as HTMLElement,
			reactive({ ghostScale: canvasProps?.scale || 1 })
		);
	}
});

const isEditable = computed(() => {
	return (
		store.builderState.editableBlock === props.block && store.activeBreakpoint === props.breakpoint // to ensure it is right block and not on different breakpoint
	);
});

const selectBlock = (e: MouseEvent | null) => {
	if (store.builderState.editableBlock === props.block || store.mode !== "select" || props.preview) {
		return;
	}
	store.selectBlock(props.block, e);
	store.activeBreakpoint = props.breakpoint;

	if (!props.preview) {
		store.leftPanelActiveTab = "Layers";
		store.rightPanelActiveTab = "Properties";
	}
};

const triggerContextMenu = (e: MouseEvent) => {
	if (props.block.isRoot() || isEditable.value) return;
	e.stopPropagation();
	e.preventDefault();
	selectBlock(e);
	nextTick(() => {
		editor.value?.element.dispatchEvent(new MouseEvent("contextmenu", e));
	});
};

const handleClick = (e: MouseEvent) => {
	if (isEditable.value) return;
	selectBlock(e);
	e.stopPropagation();
	e.preventDefault();
};

const handleDoubleClick = (e: MouseEvent) => {
	if (isEditable.value) return;
	store.builderState.editableBlock = null;
	if (Boolean(props.block.extendedFromComponent)) {
		store.editComponent(props.block);
		e.stopPropagation();
		e.preventDefault();
		return;
	}
	if (props.block.isText() || props.block.isLink() || props.block.isButton()) {
		store.builderState.editableBlock = props.block;
		e.stopPropagation();
	}

	// dblclick on container adds text block or selects text block if only one child
	let children = props.block.getChildren();
	if (props.block.isContainer()) {
		if (!children.length) {
			const child = getBlockTemplate("text");
			props.block.setBaseStyle("alignItems", "center");
			props.block.setBaseStyle("justifyContent", "center");
			const childBlock = props.block.addChild(child);
			childBlock.makeBlockEditable();
			e.stopPropagation();
		} else if (children.length === 1 && children[0].isText()) {
			const child = children[0];
			child.makeBlockEditable();
			e.stopPropagation();
		}
	}
};

const handleMouseOver = (e: MouseEvent) => {
	store.hoveredBlock = props.block.blockId;
	store.hoveredBreakpoint = props.breakpoint;
	e.stopPropagation();
};

const handleMouseLeave = (e: MouseEvent) => {
	if (store.hoveredBlock === props.block.blockId) {
		store.hoveredBlock = null;
		e.stopPropagation();
	}
};
</script>
