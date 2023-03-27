<template>
	<div class="z-10 editor fixed border-[1px] border-blue-400 box-content" ref="editor" @click.stop="handleClick"
		@mousedown.stop="handleMove" @dragstart="setCopyData($event, element, i)" @dragend="copy"
		:draggable="elementProperties.draggable !== false" :class="{
			'pointer-events-none': elementProperties.blockId === store.hoveredBlock,
		}">
		<BoxResizer v-if="selected && target" :targetProps="elementProperties" :target="target"></BoxResizer>
		<PaddingHandler v-if="selected && target" :targetProps="elementProperties" :disableHandlers="false"></PaddingHandler>
		<BorderRadiusHandler v-if="target" :targetProps="elementProperties" :target="target"></BorderRadiusHandler>
	</div>
</template>
<script setup>
import { getCurrentInstance, onMounted, ref, reactive } from "vue";
import { useDebounceFn } from "@vueuse/shared";
import useStore from "../store";
import trackTarget from "../utils/trackTarget";
import PaddingHandler from "./PaddingHandler.vue";
import BorderRadiusHandler from "./BorderRadiusHandler.vue";
import BoxResizer from "./BoxResizer.vue";

const props = defineProps(["movable", "resizable", "roundable", "resizableX", "resizableY", "element-properties", "selected"]);
const store = useStore();
const editor = ref(null);
let editorWrapper = ref(null);

let targetProps = props.elementProperties;
let target = reactive(targetProps.component);
let currentInstance = null;

onMounted(() => {
	currentInstance = getCurrentInstance();
	editorWrapper = editor.value;
	target = reactive(currentInstance.parent.refs.component);
	props.elementProperties.targetElement = target
	if (target instanceof HTMLElement) {
		trackTarget(target, editorWrapper);
	} else {
		return false;
	}
})

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
}

const handleMove = (ev) => {
	if (!props.movable) return;
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startLeft = target.offsetLeft;
	const startTop = target.offsetTop;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		const movementX = mouseMoveEvent.clientX - startX;
		const movementY = mouseMoveEvent.clientY - startY;

		targetProps.setStyle("position", "absolute");
		targetProps.setStyle("left", `${startLeft + movementX}px`);
		targetProps.setStyle("top", `${startTop + movementY}px`);
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}

const setCopyData = useDebounceFn((event, data) => {
	if (event.altKey) {
		event.dataTransfer.action = "copy";
		event.dataTransfer.data_to_copy = store.getBlockCopy(store.builderState.selectedBlock);
	}
});

const copy = useDebounceFn((event) => {
	if (event.dataTransfer.action === "copy") {
		let superParent = currentInstance.parent.parent;
		if (superParent.props?.elementProperties?.children) {
			superParent.props.elementProperties.children.push(event.dataTransfer.data_to_copy);
		} else {
			store.builderState.blocks.push(event.dataTransfer.data_to_copy);
		}
	} else {
		target.draggable = true;
		relayEventToTarget(event);
	}
});

const relayEventToTarget = (event) => {
	let eventForTarget = new window[event.constructor.name](event.type, event);
	target.dispatchEvent(eventForTarget);
	event.preventDefault();
}

</script>