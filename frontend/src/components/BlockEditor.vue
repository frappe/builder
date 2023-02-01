<template>
	<div class="z-10 editor fixed hover:border-[1px] hover:border-blue-200 group invisible"
		ref="editor" @click.stop @dblclick.stop="handleDblClick" @mousedown.stop="handleMove">
		<div class="absolute border-radius-resize w-[10px] h-[10px] border-[1px] border-blue-400 bg-white rounded-full pointer-events-auto top-2 left-2 hidden cursor-default" @mousedown.stop="handleRounded" v-if="roundable">
			<div class="absolute w-[4px] h-[4px] bg-blue-400 top-[2px] left-[2px] rounded-full pointer-events-none"></div>
		</div>
		<div class="absolute w-[4px] border-none bg-transparent top-0
			bottom-0 left-[-2px] left-handle ew-resize pointer-events-auto" >
		</div>
		<div class="absolute w-[4px] border-none bg-transparent top-0
			bottom-0 right-[-2px] right-handle cursor-ew-resize pointer-events-auto" @mousedown.stop="handleRightResize">
		</div>
		<div class="absolute h-[4px] border-none bg-transparent top-[-2px]
			right-0 left-0 top-handle ns-resize pointer-events-auto">
		</div>
		<div class="absolute h-[4px] border-none bg-transparent bottom-[-2px]
			right-0 left-0 bottom-handle cursor-ns-resize pointer-events-auto" @mousedown.stop="handleBottomResize">
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
import { getCurrentInstance, onMounted, ref } from "vue";
import useStore from "../store";
import trackTarget from "../utils/trackTarget";

const props = defineProps(["movable", "resizable", "roundable"]);
const store = useStore();
const editor = ref(null);

let target = null;
let currentInstance = null;

onMounted(() => {
	currentInstance = getCurrentInstance();
	const editorWrapper = editor.value;
	target = currentInstance.parent.refs.component;
	trackTarget(target, editorWrapper);

	if (store.selectedComponent === target) {
		// selected
		editorWrapper.querySelectorAll("[class*=resize]").forEach((element) => {
			element.classList.remove("hidden");
		});
		editorWrapper.classList.add(
			"border-[1px]",
			"border-blue-400",
		);
		editorWrapper.classList.remove(
			"invisible",
			"pointer-events-none"
		);
	}

	store.$subscribe(({ events }) => {
		console.log('in subscribe');
		if (events.key !== "selectedComponent") return;
		if (events.newValue === target) {
			// selected
			editorWrapper.querySelectorAll("[class*=resize]").forEach((element) => {
				element.classList.remove("hidden");
			});
			editorWrapper.classList.add(
				"border-[1px]",
				"border-blue-400",
			);
			editorWrapper.classList.remove(
				"invisible",
				"pointer-events-none"
			);
		} else {
			// un-selected
			editorWrapper.querySelectorAll("[class*=resize]").forEach((element) => {
				element.classList.add("hidden");
			});

			editorWrapper.classList.add(
				"invisible",
			);

			editorWrapper.classList.remove(
				"border-[1px]",
				"border-blue-400",
				// if the new selected component is a child of this component
				"pointer-events-none",
			);
		}
	});
})

const handleRightResize = (ev) => {
	const startX = ev.clientX;
	const startWidth = target.offsetWidth;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		const movement = mouseMoveEvent.clientX - startX;
		target.style.width = `${startWidth + movement}px`;
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
		const movementY = mouseMoveEvent.clientY - startY;
		target.style.height = `${startHeight + movementY}px`;

		const movementX = mouseMoveEvent.clientX - startX;
		target.style.width = `${startWidth + movementX}px`;
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
	const initialLeft = 10;
	const initialTop = 10;

	const targetBounds = target.getBoundingClientRect();
	const targetWidth = targetBounds.width;
	const targetHeight = targetBounds.height;

	const maxMovement = Math.min(targetHeight, targetWidth) / 2;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = handle.style.cursor;

	let lastX = startX;
	let lastY = startY;

	const mousemove = (mouseMoveEvent) => {
		mouseMoveEvent.preventDefault();
		const movementX = (mouseMoveEvent.clientX - lastX);
		const movementY = (mouseMoveEvent.clientY - lastY);

		let directionX = movementX > 0 ? 'right' : 'left';
		let directionY = movementY > 0 ? 'down' : 'up';

		// mean of movement on both axis
		let movement = (movementX + movementY) / 2;

		let newTop = parseInt(handleStyle.top) + movement;
		let newLeft = parseInt(handleStyle.left) + movement;

		if (newTop < initialTop) {
			newTop = initialTop;
		}
		if (newLeft < initialLeft) {
			newLeft = initialLeft;
		}

		let radius = Math.min(newTop - initialTop, newLeft - initialLeft);
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
</script>