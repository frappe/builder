<template>
	<component
		:is="getComponentName(block)"
		@click="handleClick"
		@dblclick="handleDoubleClick"
		@contextmenu="triggerContextMenu($event)"
		@mouseover="handleMouseOver"
		@mouseleave="handleMouseLeave"
		:data-block-id="block.blockId"
		:class="classes"
		v-bind="attributes"
		:style="styles"
		ref="component">
		<BuilderBlock
			:block="child"
			:breakpoint="breakpoint"
			:preview="preview"
			:isChildOfComponent="block.isComponent() || isChildOfComponent"
			v-for="child in block.getChildren()" />
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
import { computed, inject, nextTick, onMounted, ref, useAttrs } from "vue";

import getBlockTemplate from "@/utils/blockTemplate";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";
import BlockHTML from "./BlockHTML.vue";
import TextBlock from "./TextBlock.vue";

const component = ref<HTMLElement | InstanceType<typeof TextBlock> | null>(null);
const attrs = useAttrs();
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
	const attribs = { ...props.block.getAttributes(), ...attrs };
	if (props.block.isText() || props.block.isHTML() || props.block.isLink() || props.block.isButton()) {
		attribs.block = props.block;
		attribs.preview = props.preview;
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
	// let styleObj = props.block.baseStyles;
	// if (props.breakpoint === "mobile") {
	// 	styleObj = { ...styleObj, ...props.block.mobileStyles };
	// } else if (props.breakpoint === "tablet") {
	// 	styleObj = { ...styleObj, ...props.block.tabletStyles };
	// }
	// styleObj = { ...styleObj, ...props.block.rawStyles };
	return { ...props.block.getStyles(props.breakpoint), ...props.block.getEditorStyles() };
});

const loadEditor = computed(() => {
	return (
		!props.isChildOfComponent &&
		target.value &&
		props.block.getStyle("display") !== "none" &&
		store.builderState.mode !== "container" &&
		((props.block.isSelected() && props.breakpoint === store.builderState.activeBreakpoint) ||
			(props.block.isHovered() && store.hoveredBreakpoint === props.breakpoint))
	);
});

const emit = defineEmits(["mounted"]);
onMounted(async () => {
	selectBlock(null);
	setFont(props.block.getStyle("fontFamily") as string);
	await nextTick();
	emit("mounted", target.value);
});

const isEditable = computed(() => {
	return (
		store.builderState.editableBlock === props.block &&
		!(props.block.isComponent() || props.isChildOfComponent) &&
		store.builderState.activeBreakpoint === props.breakpoint // to ensure it is right block and not on different breakpoint
	);
});

const selectBlock = (e: MouseEvent | null) => {
	if (
		store.builderState.editableBlock === props.block ||
		store.builderState.mode !== "select" ||
		props.preview ||
		props.isChildOfComponent
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
	console.log(props.block);
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
	if (props.block.isText() || props.block.isLink() || props.block.isButton()) {
		store.builderState.editableBlock = props.block;
		e.stopPropagation();
	}
	if (props.block.isComponent()) {
		store.editComponent(props.block);
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

// let ghostElement = null as HTMLElement | null;

// const handleDragStart = (e: DragEvent) => {
// 	console.log(e, props.block.blockId);
// 	e.dataTransfer?.setData("block", props.block.blockId);
// 	const target = e.target as HTMLElement;
// 	ghostElement = target.cloneNode(true) as HTMLElement;
// 	ghostElement.id = "ghost";
// 	ghostElement.style.position = "fixed";
// 	ghostElement.style.transform = `scale(${canvasProps?.scale})`;
// 	document.body.appendChild(ghostElement);
// 	if (e.dataTransfer) {
// 		e.dataTransfer.effectAllowed = "move";
// 		const blankImage = document.createElement("img");
// 		e.dataTransfer.setDragImage(blankImage, e.offsetX, e.offsetY);
// 	}
// };

// const handleDrag = (e: DragEvent) => {
// 	const target = e.target as HTMLElement;
// 	ghostElement = ghostElement as HTMLElement;
// 	ghostElement.style.left = e.clientX - target.offsetWidth / 2 + "px";
// 	ghostElement.style.top = e.clientY - target.offsetHeight / 2 + "px";
// };

// const handleDragEnd = (e: DragEvent) => {
// 	const target = e.target as HTMLElement;
// 	if (ghostElement) {
// 		ghostElement.remove();
// 	}
// 	target.style.opacity = "1";
// };

// const handleDrop = (e: DragEvent) => {
// 	store.history.pause();
// 	// move block to new container
// 	if (e.dataTransfer) {
// 		const blockId = e.dataTransfer.getData("block");
// 		const block = store.findBlock(blockId);
// 		if (block) {
// 			const newParent = props.block;
// 			const oldParent = block.getParentBlock();
// 			if (newParent.blockId === oldParent?.blockId) return;
// 			if (newParent.isContainer()) {
// 				if (oldParent) {
// 					oldParent.removeChild(block);
// 				}
// 				newParent.addChild(block);
// 				store.selectBlock(block, e);
// 			}
// 		}
// 	}
// 	store.history.resume();
// };
</script>
