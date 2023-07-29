<template>
	<BlockContextMenu :block="block" :editable="editable" v-slot="{ onContextMenu }">
		<div
			class="editor pointer-events-none fixed z-[19] box-content select-none border-[1px]"
			ref="editor"
			@click="handleClick"
			@dblclick="handleDoubleClick"
			@mousedown.prevent="handleMove"
			@contextmenu="onContextMenu"
			:data-block-id="block.blockId"
			:class="getStyleClasses">
			<BlockDescription v-if="isBlockSelected && !resizing && !editable" :block="block"></BlockDescription>
			<PaddingHandler
				v-if="isBlockSelected && !resizing && !editable && store.builderState.selectedBlocks.length === 1"
				:target-block="block"
				:on-update="updateTracker"
				:disable-handlers="false"
				:breakpoint="breakpoint" />
			<MarginHandler
				v-if="isBlockSelected && !resizing && !editable && store.builderState.selectedBlocks.length === 1"
				:target-block="block"
				:on-update="updateTracker"
				:disable-handlers="false"
				:breakpoint="breakpoint" />
			<BorderRadiusHandler
				v-if="
					isBlockSelected && !block.isRoot() && !editable && store.builderState.selectedBlocks.length === 1
				"
				:target-block="block"
				:target="target" />
			<BoxResizer v-if="showResizer" :targetBlock="block" @resizing="resizing = $event" :target="target" />
		</div>
	</BlockContextMenu>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { addPxToNumber } from "@/utils/helpers";
import { Ref, computed, inject, nextTick, onMounted, ref, watch, watchEffect } from "vue";

import useStore from "../store";
import setGuides from "../utils/guidesTracker";
import trackTarget from "../utils/trackTarget";
import BlockContextMenu from "./BlockContextMenu.vue";
import BlockDescription from "./BlockDescription.vue";
import BorderRadiusHandler from "./BorderRadiusHandler.vue";
import BoxResizer from "./BoxResizer.vue";
import MarginHandler from "./MarginHandler.vue";
import PaddingHandler from "./PaddingHandler.vue";

const canvasProps = inject("canvasProps") as CanvasProps;

const showResizer = computed(() => {
	return (
		!props.block.isRoot() &&
		!props.editable &&
		isBlockSelected.value &&
		store.builderState.selectedBlocks.length === 1 &&
		!props.block.isHTML()
	);
});

const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
	breakpoint: {
		type: String,
		default: "desktop",
	},
	target: {
		type: HTMLElement,
		required: true,
	},
	editable: {
		type: Boolean,
		default: false,
	},
});
const store = useStore();
const editor = ref(null) as unknown as Ref<HTMLElement>;
const updateTracker = ref(() => {});
const resizing = ref(false);
const guides = setGuides(props.target, canvasProps);
const moving = ref(false);
const preventCLick = ref(false);

watchEffect(() => {
	props.block.getStyle("top");
	props.block.getStyle("left");
	props.block.getStyle("bottom");
	props.block.getStyle("right");
	props.block.getStyle("position");
	props.block.getParentBlock()?.getStyle("display");
	props.block.getParentBlock()?.getStyle("justifyContent");
	props.block.getParentBlock()?.getStyle("alignItems");
	props.block.getParentBlock()?.getStyle("flexDirection");
	store.builderLayout.leftPanelWidth;
	store.builderLayout.rightPanelWidth;
	store.showPanels;
	nextTick(() => {
		updateTracker.value();
	});
});

const isBlockSelected = computed(() => {
	return props.block.isSelected() && props.breakpoint === store.builderState.activeBreakpoint;
});

const getStyleClasses = computed(() => {
	const classes = [];
	if (movable.value && !props.block.isRoot()) {
		classes.push("cursor-grab");
	}
	if (props.block.isComponent) {
		classes.push("border-purple-400");
	} else {
		classes.push("border-blue-400");
	}
	if (
		props.block.isSelected() &&
		props.breakpoint === store.builderState.activeBreakpoint &&
		!props.editable &&
		!props.block.isRoot()
	) {
		classes.push("pointer-events-auto");
	}
	return classes;
});

watch(store.builderState.blocks, () => {
	nextTick(() => {
		updateTracker.value();
	});
});

const movable = computed(() => {
	return props.block.getStyle("position") === "absolute";
});

onMounted(() => {
	updateTracker.value = trackTarget(props.target, editor.value, canvasProps);
});

const handleClick = (ev: MouseEvent) => {
	if (props.editable) return;
	if (preventCLick.value) {
		preventCLick.value = false;
		return;
	}
	const editorWrapper = editor.value;
	editorWrapper.classList.add("pointer-events-none");
	let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
	if (element.classList.contains("editor")) {
		element.classList.remove("pointer-events-auto");
		element.classList.add("pointer-events-none");
		element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
	}
	if (element.classList.contains("__builder_component__")) {
		element.dispatchEvent(new MouseEvent("click", ev));
	}
};

const handleDoubleClick = () => {
	if (props.editable) return;
	if (props.block.isText() || props.block.isButton() || props.block.isLink()) {
		store.builderState.editableBlock = props.block;
	}
};

const handleMove = (ev: MouseEvent) => {
	if (store.builderState.mode === "text") {
		store.builderState.editableBlock = props.block;
	}
	if (!movable.value || props.block.isRoot()) return;
	const target = ev.target as HTMLElement;
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startLeft = props.target.offsetLeft;
	const startTop = props.target.offsetTop;
	moving.value = true;
	guides.showX();

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(target).cursor;

	const mousemove = async (mouseMoveEvent: MouseEvent) => {
		const scale = canvasProps.scale;
		const movementX = (mouseMoveEvent.clientX - startX) / scale;
		const movementY = (mouseMoveEvent.clientY - startY) / scale;
		let finalLeft = startLeft + movementX;
		await nextTick();
		const leftOffset = guides.getLeftPositionOffset();

		props.block.setStyle("left", addPxToNumber(finalLeft + leftOffset));
		props.block.setStyle("top", addPxToNumber(startTop + movementY));
		mouseMoveEvent.preventDefault();
		preventCLick.value = true;
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			moving.value = false;
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			mouseUpEvent.preventDefault();
		},
		{ once: true }
	);
};
</script>
