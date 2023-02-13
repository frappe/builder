<template>
	<div class="z-10 editor fixed border-[1px] border-blue-300" ref="editor"
		@dblclick.stop="handleDblClick" @mousedown.stop="handleMove"
		@dragstart="setCopyData($event, element, i)" @dragend="copy" draggable="true">
		<div class="absolute padding-handler hover:bg-purple-600 opacity-50 w-full cursor-ns-resize" @mousedown.stop="handlePadding" ref="paddingHandler"></div>
		<div class="absolute top-0 right-0 border-2 bg-purple-500 w-3 h-3 rounded-full opacity-50 pointer-events-auto" @click.prevent="resetPosition" v-if="movable"></div>
		<div class="absolute border-radius-resize w-[9px] h-[9px] border-[1px] border-blue-400 bg-white rounded-full pointer-events-auto top-2 left-2 cursor-default"
			@mousedown.stop="handleRounded" v-if="roundable">
			<div class="absolute w-[3px] h-[3px] bg-blue-400 top-[2px] left-[2px] border-none rounded-full pointer-events-none">
			</div>
		</div>
		<div class="absolute w-[4px] border-none bg-transparent top-0
			bottom-0 left-[-2px] left-handle ew-resize pointer-events-auto">
		</div>
		<div class="absolute w-[4px] border-none bg-transparent top-0
			bottom-0 right-[-2px] right-handle pointer-events-auto" :class="{ 'cursor-ew-resize': resizableX }"
			@mousedown.stop="handleRightResize">
		</div>
		<div class="absolute h-[4px] border-none bg-transparent top-[-2px]
			right-0 left-0 top-handle ns-resize pointer-events-auto">
		</div>
		<div class="absolute h-[4px] border-none bg-transparent bottom-[-2px]
			right-0 left-0 bottom-handle pointer-events-auto" :class="{ 'cursor-ns-resize': resizableY }"
			 @mousedown.stop="handleBottomResize">
		</div>

		<!-- <div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			top-[-4px] left-[-4px] nwse-resize pointer-events-auto">
		</div> -->
		<!-- <div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			bottom-[-4px] left-[-4px] nesw-resize pointer-events-auto">
		</div> -->
		<!-- <div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			top-[-4px] right-[-4px] nesw-resize pointer-events-auto">
		</div> -->
		<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			bottom-[-4px] right-[-4px] cursor-nwse-resize pointer-events-auto" @mousedown.stop="handleBottomCornerResize">
		</div>
	</div>
</template>
<script setup>
import { getCurrentInstance, onMounted, ref} from "vue";
import { useDebounceFn } from "@vueuse/shared";
import useStore from "../store";
import trackTarget from "../utils/trackTarget";

const props = defineProps(["movable", "resizable", "roundable", "resizableX", "resizableY"]);
const store = useStore();
const editor = ref(null);
let editorWrapper = ref(null);
let paddingHandler = ref(null);

let target = ref(null);
let currentInstance = null;

onMounted(() => {
	currentInstance = getCurrentInstance();
	editorWrapper = editor.value;
	target = currentInstance.parent.refs.component;
	const targetStyle = window.getComputedStyle(target);
	paddingHandler.value.style.height = (parseInt(targetStyle.paddingTop, 10) || 5) + "px";
	trackTarget(target, editorWrapper);
})

const handleRightResize = (ev) => {
	if (!props.resizableX) return;
	const startX = ev.clientX;
	const startWidth = target.offsetWidth;
	const parentWidth = target.parentElement.offsetWidth;
	const startWidthPercent = startWidth / parentWidth * 100;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		const movement = mouseMoveEvent.clientX - startX;
		const movementPercent = movement / parentWidth * 100;
		target.style.width = `${startWidthPercent + movementPercent}%`;
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}

const handleBottomResize = (ev) => {
	if (!props.resizableY) return;
	const startY = ev.clientY;
	const startHeight = target.offsetHeight;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		const movement = mouseMoveEvent.clientY - startY;
		target.style.height = `${startHeight + movement}px`;
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}

const handleBottomCornerResize = (ev) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const startHeight = target.offsetHeight;
	const startWidth = target.offsetWidth;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		if (props.resizableX) {
			const movementX = mouseMoveEvent.clientX - startX;
			target.style.width = `${startWidth + movementX}px`;
		}
		if (props.resizableY) {
			const movementY = mouseMoveEvent.clientY - startY;
			target.style.height = `${startHeight + movementY}px`;
		}
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}

const handleDblClick = (ev) => {
	const editorWrapper = editor.value;
	editorWrapper.classList.add("pointer-events-none");
	document.elementFromPoint(ev.x, ev.y).click();
}

const handleMove = (ev) => {
	if (!props.movable) return;
	// if (ev.altKey) {
	// 	setDraggable(ev);
	// 	return
	// }
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

		target.style.position = "absolute";
		target.style.left = `${startLeft + movementX}px`;
		target.style.top = `${startTop + movementY}px`;
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}

const handleRounded = (ev) => {
	const startX = ev.clientX;
	const startY = ev.clientY;
	const handle = ev.currentTarget;
	const handleStyle = window.getComputedStyle(handle);
	const minLeft = 10;
	const minTop = 10;

	const targetBounds = target.getBoundingClientRect();
	const targetStyle = window.getComputedStyle(target);
	const targetWidth = parseInt(targetStyle.width, 10);
	const targetHeight = parseInt(targetStyle.height, 10);

	const maxRadius = Math.min(targetHeight, targetWidth) / 2;

	// refer position based on bounding rect of target (target could have been scaled)
	const maxDistance = Math.min(targetBounds.height, targetBounds.width) / 2;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = handle.style.cursor;

	let lastX = startX;
	let lastY = startY;

	const mousemove = (mouseMoveEvent) => {
		mouseMoveEvent.preventDefault();
		const movementX = (mouseMoveEvent.clientX - lastX);
		const movementY = (mouseMoveEvent.clientY - lastY);

		// mean of movement on both axis
		const movement = (movementX + movementY) / 2;
		let radius = parseInt(target.style.borderRadius || 0, 10) + movement;
		radius = Math.max(0, Math.min(radius, maxRadius))

		const ratio = radius / maxRadius;
		const handleHeight = parseInt(handleStyle.height, 10);
		const handleWidth = parseInt(handleStyle.width, 10);
		const newTop = Math.max(minTop, ((maxDistance * ratio) - handleHeight / 2));
		const newLeft = Math.max(minLeft, ((maxDistance * ratio) - handleWidth / 2));

		target.style.borderRadius = `${radius}px`;
		handle.style.top = `${newTop}px`;
		handle.style.left = `${newLeft}px`;

		lastX = mouseMoveEvent.clientX;
		lastY = mouseMoveEvent.clientY;
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}

const setDraggable = (ev) => {
	ev.target.setAttribute("draggable", "true");
}

const setCopyData = useDebounceFn((event, data) => {
	if (event.altKey) {
		event.dataTransfer.action = "copy";
		event.dataTransfer.data_to_copy = JSON.parse(JSON.stringify(store.getBlockData(target)));
	}
});

const copy = useDebounceFn((event) => {
	if (event.dataTransfer.action === "copy") {
		let superParent = currentInstance.parent.parent;
		if (superParent.props?.elementProperties?.children) {
			superParent.props.elementProperties.children.push(event.dataTransfer.data_to_copy);
		} else {
			store.blocks.push(event.dataTransfer.data_to_copy);
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

const resetPosition = (ev) => {
	target.style.position = "relative";
	target.style.left = "0px";
	target.style.top = "0px";
}

const handlePadding = (ev) => {
	const startY = ev.clientY;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;
	paddingHandler.value.classList.add("bg-purple-600");

	const mousemove = (mouseMoveEvent) => {
		let movementY = mouseMoveEvent.clientY - startY;

		if (movementY < 0) movementY = 0;
		target.style.padding = movementY + "px";
		paddingHandler.value.style.height = (parseInt(target.style.padding, 10) || 5) + "px";
		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		paddingHandler.value.classList.remove("bg-purple-600");
		mouseUpEvent.preventDefault();
	});
}
</script>