<template>
	<BlockContextMenu :block="block" :editable="editable" v-slot="{ onContextMenu }">
		<div
			class="editor pointer-events-none fixed z-[18] box-content select-none ring-2 ring-inset"
			ref="editor"
			@click.stop="handleClick"
			@dblclick="handleDoubleClick"
			@mousedown.prevent="handleMove"
			@drop.prevent.stop="handleDrop"
			@contextmenu="onContextMenu"
			:data-block-id="block.blockId"
			:class="getStyleClasses">
			<PaddingHandler
				v-if="isBlockSelected && !resizing && !editable && !blockController.multipleBlocksSelected()"
				:target-block="block"
				:target="target"
				:on-update="updateTracker"
				:disable-handlers="false"
				:breakpoint="breakpoint" />
			<MarginHandler
				v-if="
					isBlockSelected &&
					!block.isRoot() &&
					!resizing &&
					!editable &&
					!blockController.multipleBlocksSelected()
				"
				:target-block="block"
				:target="target"
				:on-update="updateTracker"
				:disable-handlers="false"
				:breakpoint="breakpoint" />
			<BorderRadiusHandler
				v-if="
					isBlockSelected &&
					!block.isRoot() &&
					!block.isText() &&
					!block.isHTML() &&
					!block.isSVG() &&
					!editable &&
					!blockController.multipleBlocksSelected()
				"
				:target-block="block"
				:target="target" />
			<BoxResizer
				v-if="showResizer && !block.isSVG()"
				:targetBlock="block"
				@resizing="resizing = $event"
				:target="(target as HTMLElement)" />
		</div>
	</BlockContextMenu>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { addPxToNumber } from "@/utils/helpers";
import { Ref, computed, inject, nextTick, onMounted, ref, watch, watchEffect } from "vue";

import blockController from "@/utils/blockController";
import useStore from "../store";
import setGuides from "../utils/guidesTracker";
import trackTarget from "../utils/trackTarget";
import BlockContextMenu from "./BlockContextMenu.vue";
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
		!blockController.multipleBlocksSelected() &&
		!props.block.isSVG() &&
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
		type: [HTMLElement, SVGElement],
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
	const parentBlock = props.block.getParentBlock();
	parentBlock?.getStyle("display");
	parentBlock?.getStyle("justifyContent");
	parentBlock?.getStyle("alignItems");
	parentBlock?.getStyle("flexDirection");
	store.builderLayout.leftPanelWidth;
	store.builderLayout.rightPanelWidth;
	store.showRightPanel;
	store.showLeftPanel;
	store.activeBreakpoint;
	store.deviceBreakpoints.map((bp) => bp.visible);
	nextTick(() => {
		updateTracker.value();
	});
});

const isBlockSelected = computed(() => {
	return props.block.isSelected() && props.breakpoint === store.activeBreakpoint;
});

const getStyleClasses = computed(() => {
	const classes = [];
	if (movable.value && !props.block.isRoot()) {
		classes.push("cursor-grab");
	}
	if (Boolean(props.block.extendedFromComponent)) {
		classes.push("ring-purple-400");
	} else {
		classes.push("ring-blue-400");
	}
	if (
		props.block.isSelected() &&
		props.breakpoint === store.activeBreakpoint &&
		!props.editable &&
		!props.block.isRoot() &&
		!props.block.isRepeater()
	) {
		// make editor interactive
		classes.push("pointer-events-auto");
		// Place the block on the top of the stack
		classes.push("!z-[19]");
	}
	return classes;
});

watch(store.activeCanvas?.block, () => {
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

// dispatch drop event to the target block
const handleDrop = (ev: DragEvent) => {
	if (props.editable) return;
	const dropEvent = new DragEvent("drop", ev);
	props.target.dispatchEvent(dropEvent);
};

const handleDoubleClick = () => {
	if (props.editable) return;
	if (props.block.isText() || props.block.isButton() || props.block.isLink()) {
		store.editableBlock = props.block;
	}
};

const handleMove = (ev: MouseEvent) => {
	if (store.mode === "text") {
		store.editableBlock = props.block;
	}
	if (!movable.value || props.block.isRoot()) return;
	const target = ev.target as HTMLElement;
	const startX = ev.clientX;
	const startY = ev.clientY;
	const targetBounds = target.getBoundingClientRect();
	const startLeft = targetBounds.left;
	const startTop = targetBounds.top;
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
		props.block.setStyle("left", addPxToNumber(finalLeft));
		props.block.setStyle("top", addPxToNumber(startTop + movementY));
		await nextTick();
		const { leftOffset, rightOffset } = guides.getPositionOffset();
		if (leftOffset !== 0) {
			props.block.setStyle("left", addPxToNumber(finalLeft + leftOffset));
		}
		if (rightOffset !== 0) {
			props.block.setStyle("left", addPxToNumber(finalLeft + rightOffset));
		}

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
			guides.hideX();
		},
		{ once: true }
	);
};

defineExpose({
	element: editor,
});
</script>
