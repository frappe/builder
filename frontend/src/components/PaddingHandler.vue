<template>
	<div class="group" :class="{
		'opacity-40': !updating,
		'opacity-70': updating,
	}" @click.stop>
		<div
			class="padding-handler absolute pointer-events-none flex w-full"
			:style="{
				height: topPaddingHandlerHeight + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="topPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto left-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					bottom: topHandle.bottom,
					left: topHandle.left,
					height: topHandle.height + 'px',
					width: topHandle.width + 'px',
				}"
				:class="{
					'cursor-ns-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event,topPaddingHandler)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingTop }}
			</div>
		</div>
		<div
			class="padding-handler absolute pointer-events-none bottom-0 flex w-full"
			:style="{
				height: bottomPaddingHandlerHeight + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="bottomPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto left-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					top: bottomHandle.top,
					left: bottomHandle.left,
					height: bottomHandle.height + 'px',
					width: bottomHandle.width + 'px',
				}" :class="{
					'cursor-ns-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event,bottomPaddingHandler)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingBottom }}
			</div>
		</div>
		<div
			class="padding-handler absolute pointer-events-none left-0 flex h-full"
			:style="{
				width: leftPaddingHandlerWidth + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="leftPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto top-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					right: leftHandle.right,
					top: leftHandle.top,
					height: leftHandle.height + 'px',
					width: leftHandle.width + 'px',
				}" :class="{
					'cursor-ew-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event,leftPaddingHandler)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingLeft }}
			</div>
		</div>
		<div
			class="padding-handler absolute pointer-events-none right-0 flex h-full"
			:style="{
				width: rightPaddingHandlerWidth + 'px',
			}"
			:class="{
				'bg-transparent': !updating,
				'bg-purple-400': updating,
			}"
			ref="rightPaddingHandler">
			<div
				class="bg-purple-400 border-2 border-purple-500 absolute hover:scale-110 pointer-events-auto top-[50%] rounded-full" :style="{
					borderWidth: (1 * store.canvas.scale) + 'px',
					left: rightHandle.left,
					top: rightHandle.top,
					height: rightHandle.height + 'px',
					width: rightHandle.width + 'px',
				}" :class="{
					'cursor-ew-resize': !disableHandlers,
				}"
			@mousedown.stop="handlePadding($event,rightPaddingHandler)" />
			<div class="m-auto text-sm text-white" v-show="updating">
				{{ blockStyles.paddingRight }}
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
	breakpoint: {
		type: String,
		default: "desktop",
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

const blockStyles = computed(() => {
	let styleObj = props.targetProps.styles;
	if (props.breakpoint === "mobile") {
		styleObj = { ...styleObj, ...props.targetProps.mobileStyles };
	} else if (props.breakpoint === "tablet") {
		styleObj = { ...styleObj, ...props.targetProps.tabletStyles };
	}
	return styleObj;
});

const topPaddingHandlerHeight = computed(() => {
	return (parseInt(blockStyles.value.paddingTop, 10) || 5) * store.canvas.scale;
});
const bottomPaddingHandlerHeight = computed(() => {
	return (parseInt(blockStyles.value.paddingBottom, 10) || 5) * store.canvas.scale;
});
const leftPaddingHandlerWidth = computed(() => {
	return (parseInt(blockStyles.value.paddingLeft, 10) || 5) * store.canvas.scale;
});
const rightPaddingHandlerWidth = computed(() => {
	return (parseInt(blockStyles.value.paddingRight, 10) || 5) * store.canvas.scale;
});

const topHandle = computed(() => {
	return {
		width: 20 * store.canvas.scale,
		height: 5 * store.canvas.scale,
		bottom: `calc(-8px * ${store.canvas.scale})`,
		left: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});

const bottomHandle = computed(() => {
	return {
		width: 20 * store.canvas.scale,
		height: 5 * store.canvas.scale,
		top: `calc(-8px * ${store.canvas.scale})`,
		left: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});

const leftHandle = computed(() => {
	return {
		width: 5 * store.canvas.scale,
		height: 20 * store.canvas.scale,
		right: `calc(-8px * ${store.canvas.scale})`,
		top: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});

const rightHandle = computed(() => {
	return {
		width: 5 * store.canvas.scale,
		height: 20 * store.canvas.scale,
		left: `calc(-8px * ${store.canvas.scale})`,
		top: `calc(50% - ${10 * store.canvas.scale}px)`,
	};
});


const handlePadding = (ev, handler) => {
	if (props.disableHandlers) return;
	updating.value = true;
	const startY = ev.clientY;
	const startX = ev.clientX;

	const startTop = parseInt(blockStyles.value.paddingTop, 10) || 5;
	const startBottom = parseInt(blockStyles.value.paddingBottom, 10) || 5;
	const startLeft = parseInt(blockStyles.value.paddingLeft, 10) || 5;
	const startRight = parseInt(blockStyles.value.paddingRight, 10) || 5;

	// to disable cursor jitter
	const docCursor = document.body.style.cursor;
	document.body.style.cursor = window.getComputedStyle(ev.target).cursor;

	const mousemove = (mouseMoveEvent) => {
		let movement = 0;
		let affectingAxis = null;
		props.onUpdate && props.onUpdate();

		if (handler === topPaddingHandler.value) {
			movement = Math.max(startTop + mouseMoveEvent.clientY - startY, 0);
			targetProps.setStyle("paddingTop", movement + "px");
			affectingAxis = "y";
		} else if (handler === bottomPaddingHandler.value) {
			movement = Math.max(startBottom + startY - mouseMoveEvent.clientY, 0);
			targetProps.setStyle("paddingBottom", movement + "px");
			affectingAxis = "y";
		} else if (handler === leftPaddingHandler.value) {
			movement = Math.max(startLeft + mouseMoveEvent.clientX - startX, 0);
			targetProps.setStyle("paddingLeft", movement + "px");
			affectingAxis = "x";
		} else if (handler === rightPaddingHandler.value) {
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
