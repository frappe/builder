<template>
	<div ref="canvasContainer" @click.prevent.stop="store.clearSelection()">
		<div class="overlay absolute" id="overlay" ref="overlay" />
		<BlockSnapGuides></BlockSnapGuides>
		<div
			v-if="isOverDropZone"
			class="pointer-events-none absolute bottom-0 left-0 right-0 top-0 z-30 bg-cyan-300 opacity-20"></div>
		<div
			class="fixed flex gap-40"
			ref="canvas"
			:style="{
				transform: `scale(${canvasProps.scale}) translate(${canvasProps.translateX}px, ${canvasProps.translateY}px)`,
			}">
			<div class="absolute right-0 top-[-60px] flex rounded-md bg-white px-3 dark:bg-zinc-900">
				<div
					v-show="!canvasProps.scaling && !canvasProps.panning"
					class="w-auto cursor-pointer p-2"
					v-for="breakpoint in store.deviceBreakpoints"
					:key="breakpoint.device"
					@click.stop="breakpoint.visible = !breakpoint.visible">
					<FeatherIcon
						:name="breakpoint.icon"
						class="h-8 w-6"
						:class="{
							'text-gray-700 dark:text-zinc-50': breakpoint.visible,
							'text-gray-300 dark:text-zinc-500': !breakpoint.visible,
						}" />
				</div>
			</div>
			<div
				class="canvas relative flex h-full rounded-md bg-white shadow-2xl"
				:style="{
					...canvasStyles,
					background: canvasProps.background,
					width: `${breakpoint.width}px`,
				}"
				v-for="breakpoint in visibleBreakpoints"
				:key="breakpoint.device">
				<div
					class="absolute left-0 select-none text-3xl text-gray-700 dark:text-zinc-300"
					:style="{
						fontSize: `calc(${12}px * 1/${canvasProps.scale})`,
						top: `calc(${-20}px * 1/${canvasProps.scale})`,
					}"
					v-show="!canvasProps.scaling && !canvasProps.panning">
					{{ breakpoint.displayName }}
				</div>
				<BuilderBlock
					:block="block"
					v-if="showBlocks"
					:breakpoint="breakpoint.device"
					:data="store.pageData" />
			</div>
		</div>
		<div
			class="fixed bottom-12 left-[50%] z-40 flex translate-x-[-50%] items-center justify-center gap-2 rounded-lg bg-white px-3 py-2 text-center text-sm font-semibold text-gray-600 shadow-md dark:bg-zinc-900 dark:text-zinc-400"
			v-show="!canvasProps.panning">
			{{ Math.round(canvasProps.scale * 100) + "%" }}
			<div class="ml-2 cursor-pointer" @click="setScaleAndTranslate">
				<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24">
					<path
						fill="currentColor"
						d="M20 9V6h-3V4h3q.825 0 1.413.588T22 6v3h-2ZM2 9V6q0-.825.588-1.413T4 4h3v2H4v3H2Zm15 11v-2h3v-3h2v3q0 .825-.588 1.413T20 20h-3ZM4 20q-.825 0-1.413-.588T2 18v-3h2v3h3v2H4Zm12-4H8q-.825 0-1.413-.588T6 14v-4q0-.825.588-1.413T8 8h8q.825 0 1.413.588T18 10v4q0 .825-.588 1.413T16 16Zm-8-2h8v-4H8v4Zm0 0v-4v4Z" />
				</svg>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import Block from "@/utils/block";
import getBlockTemplate from "@/utils/blockTemplate";
import { addPxToNumber, getNumberFromPx } from "@/utils/helpers";
import { clamp, useDropZone, useElementBounding, useEventListener } from "@vueuse/core";
import { FeatherIcon } from "frappe-ui";
import { PropType, computed, nextTick, onMounted, provide, reactive, ref, watchEffect } from "vue";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import BuilderBlock from "./BuilderBlock.vue";

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);
const showBlocks = ref(false);
const overlay = ref(null);

const props = defineProps({
	block: {
		type: Block,
		default: false,
	},
	canvasProps: {
		type: Object as PropType<CanvasProps>,
		default: () => ({}),
	},
	canvasStyles: {
		type: Object,
		default: () => ({}),
	},
});

provide("canvasProps", props.canvasProps);

onMounted(() => {
	props.canvasProps.overlayElement = overlay.value;
	setEvents();
});

const { isOverDropZone } = useDropZone(canvasContainer, {
	onDrop: (files, ev) => {
		let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		let parentBlock = props.block;
		if (element) {
			if (element.dataset.blockId) {
				parentBlock = store.findBlock(element.dataset.blockId) || parentBlock;
			}
		}
		let componentName = ev.dataTransfer?.getData("componentName");
		if (componentName) {
			const newBlock = store.getBlockCopy(webComponent.getRow(componentName).block, true);
			newBlock.extendFromComponent(componentName);
			parentBlock.addChild(newBlock);
			ev.stopPropagation();
		} else if (files && files.length) {
			store.uploadFile(files[0]).then((fileDoc: { fileURL: string; fileName: string }) => {
				if (parentBlock.isImage()) {
					parentBlock.setAttribute("src", fileDoc.fileURL);
					parentBlock.setAttribute("alt", fileDoc.fileName);
				} else if (parentBlock.isContainer() && ev.shiftKey) {
					parentBlock.setStyle("background", `url(${fileDoc.fileURL})`);
				} else {
					parentBlock.addChild(store.getImageBlock(fileDoc.fileURL, fileDoc.fileName));
				}
			});
		}
	},
});

const visibleBreakpoints = computed(() => {
	return store.deviceBreakpoints.filter(
		(breakpoint) => breakpoint.visible || breakpoint.device === "desktop"
	);
});

function setEvents() {
	const container = document.body.querySelector(".canvas-container") as HTMLElement;
	useEventListener(container, "mousedown", (ev: MouseEvent) => {
		const initialX = ev.clientX;
		const initialY = ev.clientY;
		if (store.mode === "select") {
			return;
		} else {
			store.history.pause();
			ev.stopPropagation();
			let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
			let block = store.getFirstBlock();
			if (element) {
				if (element.dataset.blockId) {
					block = store.findBlock(element.dataset.blockId) || block;
				}
			}
			let parentBlock = store.getFirstBlock();
			if (element.dataset.blockId) {
				parentBlock = store.findBlock(element.dataset.blockId) || parentBlock;
				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock() || store.getFirstBlock();
				}
			}
			const child = getBlockTemplate(store.mode);
			const parentElement = document.body.querySelector(
				`.canvas [data-block-id="${parentBlock.blockId}"]`
			) as HTMLElement;
			const parentOldPosition = parentBlock.getStyle("position");
			parentBlock.setBaseStyle("position", parentOldPosition || "relative");
			const parentElementBounds = parentElement.getBoundingClientRect();
			let x = (ev.x - parentElementBounds.left) / props.canvasProps.scale;
			let y = (ev.y - parentElementBounds.top) / props.canvasProps.scale;
			const parentWidth = getNumberFromPx(getComputedStyle(parentElement).width);
			const parentHeight = getNumberFromPx(getComputedStyle(parentElement).height);

			const childBlock = parentBlock.addChild(child);
			childBlock.setBaseStyle("position", "absolute");
			childBlock.setBaseStyle("top", addPxToNumber(y));
			childBlock.setBaseStyle("left", addPxToNumber(x));

			const mouseMoveHandler = (mouseMoveEvent: MouseEvent) => {
				if (store.mode === "text" || store.mode === "html") {
					return;
				} else {
					mouseMoveEvent.preventDefault();
					let width = (mouseMoveEvent.clientX - initialX) / props.canvasProps.scale;
					let height = (mouseMoveEvent.clientY - initialY) / props.canvasProps.scale;
					width = clamp(width, 0, parentWidth);
					height = clamp(height, 0, parentHeight);
					childBlock.setBaseStyle("width", addPxToNumber(width));
					childBlock.setBaseStyle("height", addPxToNumber(height));
				}
			};
			useEventListener(document, "mousemove", mouseMoveHandler);
			useEventListener(
				document,
				"mouseup",
				() => {
					document.removeEventListener("mousemove", mouseMoveHandler);
					childBlock.setBaseStyle("position", "static");
					childBlock.setBaseStyle("top", "auto");
					childBlock.setBaseStyle("left", "auto");
					if (store.mode === "text" || store.mode === "html") {
						store.history.resume();
					}
					if (getNumberFromPx(childBlock.getStyle("width")) < 100) {
						childBlock.setBaseStyle("width", "100%");
					}
					if (getNumberFromPx(childBlock.getStyle("height")) < 100) {
						childBlock.setBaseStyle("height", "200px");
					}
					parentBlock.setBaseStyle("position", parentOldPosition || "static");
					setTimeout(() => {
						store.mode = "select";
					}, 50);
					store.history.resume();
				},
				{ once: true }
			);
		}
	});
}

const containerBound = reactive(useElementBounding(canvasContainer));
const canvasBound = reactive(useElementBounding(canvas));

const setScaleAndTranslate = async () => {
	if (document.readyState !== "complete") {
		await new Promise((resolve) => {
			window.addEventListener("load", resolve);
		});
	}
	const paddingX = 300;
	const paddingY = 400;

	await nextTick();
	canvasBound.update();
	const containerWidth = containerBound.width;
	const containerHeight = containerBound.height;

	const canvasWidth = canvasBound.width / props.canvasProps.scale;
	const canvasHeight = canvasBound.height / props.canvasProps.scale;

	props.canvasProps.scale = Math.min(
		containerWidth / (canvasWidth + paddingX * 2),
		containerHeight / (canvasHeight + paddingY * 2)
	);

	props.canvasProps.translateX = 0;
	props.canvasProps.translateY = 0;
	await nextTick();
	const scale = props.canvasProps.scale;
	canvasBound.update();
	const diffY = containerBound.top - canvasBound.top + paddingY * scale;
	if (diffY !== 0) {
		props.canvasProps.translateY = diffY / scale;
	}
	props.canvasProps.settingCanvas = false;
};

onMounted(() => {
	setScaleAndTranslate();
	const canvasContainerEl = canvasContainer.value as unknown as HTMLElement;
	const canvasEl = canvas.value as unknown as HTMLElement;
	setPanAndZoom(props.canvasProps, canvasEl, canvasContainerEl);
	showBlocks.value = true;
});

const resetZoom = () => {
	props.canvasProps.scale = 1;
	props.canvasProps.translateX = 0;
	props.canvasProps.translateY = 0;
};

const moveCanvas = (direction: "up" | "down" | "right" | "left") => {
	if (direction === "up") {
		props.canvasProps.translateY -= 20;
	} else if (direction === "down") {
		props.canvasProps.translateY += 20;
	} else if (direction === "right") {
		props.canvasProps.translateX += 20;
	} else if (direction === "left") {
		props.canvasProps.translateX -= 20;
	}
};

const zoomIn = () => {
	props.canvasProps.scale += 0.1;
};

const zoomOut = () => {
	props.canvasProps.scale -= 0.1;
};

defineExpose({
	setScaleAndTranslate,
	resetZoom,
	moveCanvas,
	zoomIn,
	zoomOut,
});

watchEffect(() => {
	store.deviceBreakpoints.map((b) => b.visible);
	if (props.canvasProps.settingCanvas) {
		return;
	}
	setScaleAndTranslate();
});

watchEffect(() => {
	toggleMode(store.mode);
});

function toggleMode(mode: BuilderMode) {
	if (!canvasContainer.value) return;
	const container = canvasContainer.value as HTMLElement;
	if (mode === "text") {
		container.style.cursor = "text";
	} else if (["container", "image", "html"].includes(mode)) {
		container.style.cursor = "crosshair";
	} else {
		container.style.cursor = "default";
	}
}
</script>
