<template>
	<div
		class="editor fixed z-[19] box-content border-[1px] border-blue-400"
		ref="editor"
		@click.stop="handleClick"
		@mousedown.stop="handleMove"
		@dragstart="setCopyData($event, element, i)"
		@dragend="copy"
		@contextmenu.prevent="showContextMenu"
		:draggable="elementProperties.draggable !== false"
		:class="{
			'pointer-events-none': elementProperties.blockId === store.hoveredBlock,
		}">
		<BoxResizer
			v-if="selected && target && !elementProperties.isRoot()"
			:targetProps="elementProperties"
			:target="target"></BoxResizer>
		<PaddingHandler v-if="selected && target" :targetProps="elementProperties" :disableHandlers="false">
		</PaddingHandler>
		<BorderRadiusHandler
			v-if="selected && target && !elementProperties.isRoot()"
			:targetProps="elementProperties"
			:target="target"></BorderRadiusHandler>
		<ContextMenu
			v-if="contextMenuVisible"
			:posX="posX"
			:posY="posY"
			:options="contextMenuOptions"
			@select="handleContextMenuSelect"
			v-on-click-outside="() => (contextMenuVisible = false)" />
		<Dialog
			class="z-40"
			:options="{
				title: 'New Component',
				size: 'sm',
				actions: [
					{
						label: 'Save',
						appearance: 'primary',
						handler: ({ close }) => {
							createComponent.submit({
								block: elementProperties,
								component_name: componentName,
							});
							close();
						},
					},
					{ label: 'Cancel' },
				],
			}"
			v-model="showDialog">
			<template #body-content>
				<Input type="text" v-model="componentName" label="Component Name" required />
			</template>
		</Dialog>
	</div>
</template>
<script setup>
import { vOnClickOutside } from "@vueuse/components";
import { useDebounceFn } from "@vueuse/shared";
import { Dialog, Input, createResource } from "frappe-ui";
import { getCurrentInstance, nextTick, onMounted, reactive, ref } from "vue";

import useStore from "../store";
import setGuides from "../utils/guidesTracker";
import trackTarget from "../utils/trackTarget";
import BorderRadiusHandler from "./BorderRadiusHandler.vue";
import BoxResizer from "./BoxResizer.vue";
import ContextMenu from "./ContextMenu.vue";
import PaddingHandler from "./PaddingHandler.vue";

const props = defineProps([
	"movable",
	"resizable",
	"roundable",
	"resizableX",
	"resizableY",
	"element-properties",
	"selected",
]);
const store = useStore();
const editor = ref(null);
let editorWrapper = ref(null);
let targetProps = props.elementProperties;
let currentInstance = null;
let guides = null;
let target = ref(null);

onMounted(() => {
	currentInstance = getCurrentInstance();
	editorWrapper = editor.value;
	target.value = currentInstance.parent.refs.component;
	guides = setGuides(target);
	props.elementProperties.targetElement = target;
	trackTarget(target.value, editorWrapper);
});

const handleClick = (ev) => {
	const editorWrapper = editor.value;
	editorWrapper.classList.add("pointer-events-none");
	let element = document.elementFromPoint(ev.x, ev.y);
	// ignore draggable blocks, select the real element instead
	while (element.classList.contains("block-draggable")) {
		element.classList.remove("pointer-events-auto");
		element.classList.add("pointer-events-none");
		element = document.elementFromPoint(ev.x, ev.y);
	}
	element.click();
};

const handleMove = (ev) => {
	// if (!props.movable) return;
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startLeft = target.offsetLeft;
	const startTop = target.offsetTop;
	guides.showX();

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = async (mouseMoveEvent) => {
		const scale = store.canvas.scale;
		const movementX = (mouseMoveEvent.clientX - startX) / scale;
		const movementY = (mouseMoveEvent.clientY - startY) / scale;
		let finalLeft = startLeft + movementX;
		await nextTick();
		const leftOffset = guides.getLeftPositionOffset(startLeft + movementX);

		targetProps.setStyle("position", "absolute");
		targetProps.setStyle("left", `${finalLeft + leftOffset}px`);
		targetProps.setStyle("top", `${startTop + movementY}px`);
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
};

const setCopyData = useDebounceFn((event, data) => {
	if (event.altKey) {
		event.dataTransfer.action = "copy";
		event.dataTransfer.data_to_copy = store.getBlockCopy(store.builderState.selectedBlock);
	}
});

const copy = useDebounceFn((event) => {
	if (event.dataTransfer.action === "copy") {
		duplicateBlock(event.dataTransfer.data_to_copy);
	} else {
		target.draggable = true;
		relayEventToTarget(event);
	}
});

const relayEventToTarget = (event) => {
	let eventForTarget = new window[event.constructor.name](event.type, event);
	target.dispatchEvent(eventForTarget);
	event.preventDefault();
};

// Context menu
const contextMenuVisible = ref(false);
const posX = ref(0);
const posY = ref(0);
const showDialog = ref(false);
const componentName = ref(null);

const showContextMenu = (event) => {
	event.preventDefault();
	contextMenuVisible.value = true;
	posX.value = event.pageX;
	posY.value = event.pageY;
};

const handleContextMenuSelect = (action) => {
	action();
	contextMenuVisible.value = false;
};

const copyStyle = () => {
	store.copiedStyle = {
		blockId: props.elementProperties.blockId,
		style: props.elementProperties.getStylesCopy(),
	};
};

const createComponent = createResource({
	url: "website_builder.website_builder.doctype.web_page_component.web_page_component.create_component",
	method: "POST",
	transform(data) {
		data.block = JSON.parse(data.block);
		return data;
	},
	onSuccess(component) {
		store.sidebarActiveTab = "Components";
		store.components.push(component);
	},
});

const saveAsComponent = () => {
	showDialog.value = true;
};

const duplicateBlock = (block) => {
	if (!block) {
		block = store.getBlockCopy(store.builderState.selectedBlock);
	}
	let superParent = currentInstance.parent.parent;
	if (superParent.props?.elementProperties?.children) {
		superParent.props.elementProperties.children.push(block);
	} else {
		store.builderState.blocks.push(block);
	}
};

const pasteStyle = () => {
	Object.assign(store.builderState.selectedBlock, store.copiedStyle.style);
};

const contextMenuOptions = [
	{ label: "Copy Style", action: copyStyle },
	{
		label: "Paste Style",
		action: pasteStyle,
		condition: () => store.copiedStyle && store.copiedStyle.blockId !== props.elementProperties.blockId,
	},
	{ label: "Save as Component", action: saveAsComponent },
	{ label: "Duplicate", action: duplicateBlock },
];
</script>
