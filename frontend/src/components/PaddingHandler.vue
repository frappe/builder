<template>
	<div class="group opacity-60">
		<div
			class="padding-handler absolute flex w-full bg-purple-400"
			:style="{
				height: topPaddingHandlerHeight + 'px',
			}"
			:class="{
				'cursor-ns-resize': !disableHandlers,
			}"
			@mousedown.stop="handlePadding"
			ref="topPaddingHandler">
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ targetProps.styles.paddingTop }}
			</div>
		</div>
		<div
			class="padding-handler absolute bottom-0 flex w-full bg-purple-400"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
			}"
			:class="{
				'cursor-ns-resize': !disableHandlers,
			}"
			@mousedown.stop="handlePadding"
			ref="bottomPaddingHandler">
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ targetProps.styles.paddingBottom }}
			</div>
		</div>
		<div
			class="padding-handler absolute left-0 flex h-full bg-purple-400"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
			}"
			:class="{
				'cursor-ew-resize': !disableHandlers,
			}"
			@mousedown.stop="handlePadding"
			ref="leftPaddingHandler">
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ targetProps.styles.paddingLeft }}
			</div>
		</div>
		<div
			class="padding-handler absolute right-0 flex h-full bg-purple-400"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
			}"
			:class="{
				'cursor-ew-resize': !disableHandlers,
			}"
			@mousedown.stop="handlePadding"
			ref="rightPaddingHandler">
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ targetProps.styles.paddingRight }}
			</div>
		</div>
	</div>
</template>
<script setup>
import useStore from "../store";
import { ref, computed, watchEffect } from "vue";
import BlockProperties from "../utils/blockProperties";
const props = defineProps({
	targetProps: {
		type: BlockProperties,
		required: true,
	},
	disableHandlers: {
		type: Boolean,
		default: false,
	},
	onUpdate: {
		type: Function,
		default: null,
	},
});

const store = useStore();
const targetProps = props.targetProps;

// Padding handlers
const topPaddingHandler = ref(null);
const bottomPaddingHandler = ref(null);
const leftPaddingHandler = ref(null);
const rightPaddingHandler = ref(null);

const updating = ref(false);
const emit = defineEmits(["update"]);

watchEffect(() => {
	emit("update", updating.value);
});

console.log(targetProps);

const topPaddingHandlerHeight = computed(() => {
	return (parseInt(targetProps.styles.paddingTop, 10) || 5) * store.canvas.scale;
});
const bottomPaddingHandlerHeight = computed(() => {
	return (parseInt(targetProps.styles.paddingBottom, 10) || 5) * store.canvas.scale;
});
const leftPaddingHandlerWidth = computed(() => {
	return (parseInt(targetProps.styles.paddingLeft, 10) || 5) * store.canvas.scale;
});
const rightPaddingHandlerWidth = computed(() => {
	return (parseInt(targetProps.styles.paddingRight, 10) || 5) * store.canvas.scale;
});

const handlePadding = (ev) => {
	if (props.disableHandlers) return;
	updating.value = true;
	const startY = ev.clientY;
	const startX = ev.clientX;

	const startTop = parseInt(targetProps.styles.paddingTop, 10) || 5;
	const startBottom = parseInt(targetProps.styles.paddingBottom, 10) || 5;
	const startLeft = parseInt(targetProps.styles.paddingLeft, 10) || 5;
	const startRight = parseInt(targetProps.styles.paddingRight, 10) || 5;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		let movement = 0;
		let affectingAxis = null;
		props.onUpdate && props.onUpdate();

		if (ev.target === topPaddingHandler.value) {
			movement = Math.max(startTop + mouseMoveEvent.clientY - startY, 0);
			targetProps.setStyle("paddingTop", movement + "px");
			affectingAxis = "y";
		} else if (ev.target === bottomPaddingHandler.value) {
			movement = Math.max(startBottom + startY - mouseMoveEvent.clientY, 0);
			targetProps.setStyle("paddingBottom", movement + "px");
			affectingAxis = "y";
		} else if (ev.target === leftPaddingHandler.value) {
			movement = Math.max(startLeft + mouseMoveEvent.clientX - startX, 0);
			targetProps.setStyle("paddingLeft", movement + "px");
			affectingAxis = "x";
		} else if (ev.target === rightPaddingHandler.value) {
			movement = Math.max(startRight + startX - mouseMoveEvent.clientX, 0);
			targetProps.setStyle("paddingRight", movement + "px");
			affectingAxis = "x";
		}

		if (mouseMoveEvent.shiftKey) {
			if (affectingAxis === "y") {
				targetProps.setStyle("paddingTop", movement + "px");
				targetProps.setStyle("paddingBottom", movement + "px");
			} else if (affectingAxis === "x") {
				targetProps.setStyle("paddingLeft", movement + "px");
				targetProps.setStyle("paddingRight", movement + "px");
			}
		}

		mouseMoveEvent.preventDefault();
	};
	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", (mouseUpEvent) => {
		document.body.style.cursor = docCursor;
		document.removeEventListener("mousemove", mousemove);
		updating.value = false;
		mouseUpEvent.preventDefault();
	});
};
</script>
