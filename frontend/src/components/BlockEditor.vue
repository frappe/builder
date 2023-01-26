<template>
	<div class="z-10 editor fixed hover:border-[1px] hover:border-blue-200 group" ref="editor" @click.stop="handleClick">
		<div class="absolute top-[-32px] w-auto h-auto pointer-events-auto">
			<Dropdown
				:options="[{label: 'H1', value: 'h1', handler: () => setType('h1')}, {label: 'H2', value: 'h2', handler: () => setType('h1')}]"
				:button="{ label: 'Font'}">
			</Dropdown>
		</div>
		<div class="absolute w-[8px] h-[8px] bg-white rounded-full pointer-events-auto top-2 right-2" @mousedown.stop="handleRounded"></div>
		<div class="absolute top-[-15px] right-0 cursor-move pointer-events-auto" @mousedown.stop="handleMove" v-if="movable">
			<FeatherIcon name="move" class="w-3 h-3 text-gray-800"></FeatherIcon>
		</div>
		<div class="absolute w-[4px] border-none bg-transparent top-0
			bottom-0 left-[-2px] left-handle cursor-ew-resize pointer-events-auto" >
		</div>
		<div class="absolute w-[4px] border-none bg-transparent top-0
			bottom-0 right-[-2px] right-handle cursor-ew-resize pointer-events-auto" @mousedown.stop="handleRightResize">
		</div>
		<div class="absolute h-[4px] border-none bg-transparent top-[-2px]
			right-0 left-0 top-handle cursor-ns-resize pointer-events-auto">
		</div>
		<div class="absolute h-[4px] border-none bg-transparent bottom-[-2px]
			right-0 left-0 bottom-handle cursor-ns-resize pointer-events-auto" @mousedown.stop="handleBottomResize">
		</div>

		<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			top-[-4px] left-[-4px] cursor-nwse-resize pointer-events-auto">
		</div>
		<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			bottom-[-4px] left-[-4px] cursor-nesw-resize pointer-events-auto">
		</div>
		<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			top-[-4px] right-[-4px] cursor-nesw-resize pointer-events-auto">
		</div>
		<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white
			bottom-[-4px] right-[-4px] cursor-nwse-resize pointer-events-auto">
		</div>
	</div>
</template>
<script setup>
import { defineProps, onMounted, ref, onUnmounted, getCurrentInstance } from "vue";
import useStore from "../store";
import { Dropdown } from "frappe-ui";

const props = defineProps(["movable"]);

const store = useStore();
const editor = ref(null);
let target = null;
let currentInstance = null;

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

const handleClick = (ev) => {
	console.log('click');
	target.click();
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

onMounted(() => {
	currentInstance = getCurrentInstance();
	const editorWrapper = editor.value;
	target = currentInstance.parent.refs.component;
	updateEditor();
	target.closest(".canvas-container").addEventListener("wheel", updateEditor);
	window.addEventListener("resize", updateEditor);
	window.addEventListener("scroll", updateEditor);

	const observer = new MutationObserver(updateEditor);
	const observer_config = {
		attributes: true,
		subtree: true,
	};
	console.log(observer.observe(target, observer_config));
	observer.observe(target.closest(".canvas"), {
		...observer_config,
		childList: true,
	});

	if (store.selectedComponent === target) {
		// selected
		editorWrapper.querySelectorAll("[class*=resize]").forEach((element) => {
			element.classList.remove("hidden");
		});
		editorWrapper.classList.add(
			"pointer-events-none",
			"border-[1px]",
			"border-blue-400",
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
				"pointer-events-none",
				"border-[1px]",
				"border-blue-400",
			);
		} else {
			// un-selected
			editorWrapper.querySelectorAll("[class*=resize]").forEach((element) => {
				element.classList.add("hidden");
			});
			editorWrapper.classList.remove(
				"border-[1px]",
				"border-blue-400",
				// if the new selected component is a child of this component
				target.contains(events.newValue) ? "pointer-events-none" : null,
			);
		}
	});
})

onUnmounted(() => {
	target.closest(".canvas-container").removeEventListener("wheel", updateEditor);
	window.removeEventListener("resize", updateEditor);
	window.removeEventListener("scroll", updateEditor);
})

function updateEditor() {
	const bound = target.getBoundingClientRect();
	const editorWrapper = editor.value;
	editorWrapper.style.width = `${bound.width}px`;
	editorWrapper.style.height = `${bound.height}px`;
	editorWrapper.style.top = `${bound.top}px`;
	editorWrapper.style.right = `${bound.right}px`;
	editorWrapper.style.left = `${bound.left}px`;
	editorWrapper.style.right = `${bound.right}px`;
}


const setType = (type) => {
	currentInstance.parent.props.elementProperties.element = type;
	console.log(currentInstance.parent.refs)
	console.log(target, currentInstance.parent.refs.component)
}

const handleRounded = (ev) => {
	let startX = ev.clientX;
	let startY = ev.clientY;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		mouseMoveEvent.preventDefault();
		const movementX = mouseMoveEvent.clientX - startX;
		const movementY = mouseMoveEvent.clientY - startY;
		mouseMoveEvent.target.style.top = movementY + "px";
		mouseMoveEvent.target.style.right = movementX + "px";
		target.style.borderRadius = movementX + "px";
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		mouseUpEvent.preventDefault();
	});
}
</script>