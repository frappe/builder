<template>
	<div
		class="editor fixed z-[19] box-content border-[1px] border-blue-400"
		ref="editor"
		@click.stop="handleClick"
		@mousedown.stop="handleMove"
		@contextmenu.prevent="showContextMenu"
		:class="{
			'pointer-events-none': block.blockId === store.hoveredBlock,
		}">
		<BoxResizer
			v-if="selected && target && !block.isRoot()"
			:target-block="block"
			@resizing="resizing = $event"
			:target="target" />
		<PaddingHandler
			v-if="selected && target && !resizing"
			:target-block="block"
			:on-update="updateTracker"
			:disable-handlers="false"
			:breakpoint="breakpoint" />
		<BorderRadiusHandler
			v-if="selected && target && !block.isRoot()"
			:target-block="block"
			:target="target" />
		<ContextMenu
			v-if="contextMenuVisible"
			:pos-x="posX"
			:pos-y="posY"
			:options="contextMenuOptions"
			@select="handleContextMenuSelect"
			v-on-click-outside="() => (contextMenuVisible = false)" />
		<Dialog
			style="z-index: 40;"
			:options="{
				title: 'New Template',
				size: 'sm',
				actions: [
					{
						label: 'Save',
						appearance: 'primary',
						handler: ({ close }) => {
							createComponent.submit({
								block: block,
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
				<Input type="text" v-model="componentName" label="Template Name" required />
			</template>
		</Dialog>
	</div>
</template>
<script setup>
import { vOnClickOutside } from "@vueuse/components";
import { useDebounceFn } from "@vueuse/shared";
import { Dialog, Input, createResource } from "frappe-ui";
import { getCurrentInstance, nextTick, onMounted, ref, reactive } from "vue";

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
	"block",
	"selected",
	"breakpoint"
]);
const store = useStore();
const editor = ref(null);
const editorWrapper = ref(null);
const target = ref(null);
const updateTracker = ref(null);
const resizing = ref(false);
const block = reactive(props.block);

let currentInstance = null;
let guides = null;

onMounted(() => {
	currentInstance = getCurrentInstance();
	editorWrapper.value = editor.value;
	target.value = currentInstance.parent.refs.component.targetDomElement;
	guides = setGuides(target);
	updateTracker.value = trackTarget(target.value, editorWrapper.value);
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
	if (!props.movable) return;
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startLeft = target.value.offsetLeft;
	const startTop = target.value.offsetTop;
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

		block.setStyle("position", "absolute");
		block.setStyle("left", `${finalLeft + leftOffset}px`);
		block.setStyle("top", `${startTop + movementY}px`);
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
		target.value.draggable = true;
		relayEventToTarget(event);
	}
});

const relayEventToTarget = (event) => {
	let eventForTarget = new window[event.constructor.name](event.type, event);
	target.value.dispatchEvent(eventForTarget);
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
		blockId: props.block.blockId,
		style: props.block.getStylesCopy(),
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
	let blockToDuplicate = block || store.getBlockCopy(store.builderState.selectedBlock);
	let superParent = currentInstance.parent.parent;
	if (superParent.props?.block?.children) {
		superParent.props.block.children.push(blockToDuplicate);
	} else {
		store.builderState.blocks.push(blockToDuplicate);
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
		condition: () => store.copiedStyle && store.copiedStyle.blockId !== props.block.blockId,
	},
	{ label: "Save as Template", action: saveAsComponent },
	{ label: "Duplicate", action: duplicateBlock },
];
</script>
