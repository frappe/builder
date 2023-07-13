<template>
	<draggable
		:list="block.children"
		:sort="true"
		:disabled="preview"
		:group="{ name: 'blocks' }"
		item-key="blockId"
		:tag="block.getTag()"
		@click="handleClick"
		@dblclick="handleDoubleClick"
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
				style: { ...styles, ...block.getEditorStyles() },
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
			v-if="
				component &&
				store.builderState.mode !== 'container' &&
				component.targetDomElement &&
				((block.isSelected() && breakpoint === store.builderState.activeBreakpoint) ||
					(block.isHovered() && store.hoveredBreakpoint === breakpoint))
			"
			v-show="!canvasProps.scaling && !canvasProps.panning"
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
import { Ref, computed, inject, nextTick, onMounted, ref, watchEffect } from "vue";
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

const canvasProps = !props.preview ? inject("canvasProps") : null;

const emit = defineEmits(["renderComplete"]);

onMounted(() => {
	selectBlock(null);
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
	selectBlock(e);
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
		selectBlock(e);
		e.stopPropagation();
		e.preventDefault();
	}
};

const handleDoubleClick = (e: MouseEvent) => {
	store.builderState.editableBlock = null;
	if (props.block.isText()) {
		store.builderState.editableBlock = props.block;
		e.stopPropagation();
	}
	if (props.block.isComponent) {
		store.editingComponent = props.block;
		e.stopPropagation();
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
