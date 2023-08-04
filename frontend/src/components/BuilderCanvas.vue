<template>
	<div ref="canvasContainer">
		<div class="overlay absolute" id="overlay" ref="overlay" />
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
					background: canvasProps.background,
					width: `${breakpoint.width}px`,
					...canvasStyles,
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
				<BuilderBlock :block="block" v-if="showBlocks" :breakpoint="breakpoint.device" />
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
import blockController from "@/utils/blockController";
import { useDebouncedRefHistory, useDropZone, useElementBounding } from "@vueuse/core";
import { FeatherIcon, FileUploadHandler, toast } from "frappe-ui";
import { storeToRefs } from "pinia";
import { PropType, computed, nextTick, onMounted, provide, reactive, ref } from "vue";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BuilderBlock from "./BuilderBlock.vue";

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);
const showBlocks = ref(false);
const overlay = ref(null);

// TODO:
store.overlayElement = overlay;

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

// const targetIsVisible = ref(false);

// const { stop } = useIntersectionObserver(canvas, ([{ isIntersecting }], observerElement) => {
// 	targetIsVisible.value = isIntersecting;
// });

// watchEffect(() => {
// 	console.log("targetIsVisible", targetIsVisible.value);
// });

const { isOverDropZone } = useDropZone(canvasContainer, {
	onDrop: (files, ev) => {
		let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		let block = props.block;
		if (element) {
			if (element.dataset.blockId) {
				block = store.findBlock(element.dataset.blockId) || block;
			}
		}
		let componentName = ev.dataTransfer?.getData("componentName");
		if (componentName) {
			const blockCopy = store.getBlockCopy(webComponent.getRow(componentName).block);
			block.addChild(blockCopy, 0, componentName);
			ev.stopPropagation();
		} else if (files && files.length) {
			const uploader = new FileUploadHandler();
			uploader
				.upload(files[0], {
					private: false,
					optimize: true,
				})
				.then((fileDoc: { file_url: string; file_name: string }) => {
					const url = encodeURI(window.location.origin + fileDoc.file_url);
					if (block.isImage()) {
						block.setAttribute("src", url);
						block.setAttribute("alt", fileDoc.file_name);
					} else {
						block.addChild(store.getImageBlock(url, fileDoc.file_name));
					}
				});
		}
	},
});

const clearSelectedComponent = () => {
	blockController.clearSelection();
	store.builderState.editableBlock = null;
	if (document.activeElement instanceof HTMLElement) {
		document.activeElement.blur();
	}
};

const visibleBreakpoints = computed(() => {
	return store.deviceBreakpoints.filter(
		(breakpoint) => breakpoint.visible || breakpoint.device === "desktop"
	);
});

document.addEventListener("keydown", (e) => {
	const target = e.target as HTMLElement;
	if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
		return;
	}
	if (e.key === "Backspace" && blockController.isBLockSelected() && !target.isContentEditable) {
		function findBlockAndRemove(blocks: Array<Block>, blockId: string) {
			if (blockId === "root") {
				toast({
					title: "Warning",
					text: "Cannot Delete Root Block",
					icon: "alert-circle",
					iconClasses: "text-yellow-500",
					position: "top-left",
				});
				return false;
			}
			blocks.forEach((block, i) => {
				if (block.blockId === blockId) {
					blocks.splice(i, 1);
					nextTick(() => {
						// select the next sibling block
						if (blocks.length && blocks[i]) {
							blocks[i].selectBlock();
						}
					});
					return true;
				} else if (block.children) {
					return findBlockAndRemove(block.children, blockId);
				}
			});
		}
		for (const block of blockController.getSelectedBlocks()) {
			findBlockAndRemove(store.builderState.blocks, block.blockId);
		}
		clearSelectedComponent();
		e.stopPropagation();
		return;
	}

	if (e.key === "Escape") {
		store.editPage(true);
		clearSelectedComponent();
	}

	// handle arrow keys
	if (e.key.startsWith("Arrow") && blockController.isBLockSelected()) {
		const key = e.key.replace("Arrow", "").toLowerCase() as "up" | "down" | "left" | "right";
		for (const block of blockController.getSelectedBlocks()) {
			block.move(key);
		}
	}
});

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

const { builderState } = storeToRefs(store);

store.history = useDebouncedRefHistory(builderState, {
	capacity: 50,
	deep: true,
	clone: (obj) => {
		let newObj = Object.assign({}, obj);
		newObj.blocks = obj.blocks.map((val) => store.getBlockCopy(val, true));
		return newObj;
	},
	debounce: 200,
}) as unknown as typeof store.history;

document.addEventListener("keydown", (e) => {
	const target = e.target as HTMLElement;
	if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.getAttribute("contenteditable")) {
		return;
	}
	if (e.key === "z" && e.metaKey && !e.shiftKey && store.history.canUndo) {
		store.history.undo();
	}
	if (e.key === "z" && e.shiftKey && e.metaKey && store.history.canRedo) {
		store.history.redo();
	}

	if (e.metaKey || e.ctrlKey || e.shiftKey) {
		return;
	}

	if (e.key === "c") {
		store.builderState.mode = "container";
	}

	if (e.key === "i") {
		store.builderState.mode = "image";
	}

	if (e.key === "t") {
		store.builderState.mode = "text";
	}

	if (e.key === "v") {
		store.builderState.mode = "select";
	}
});

defineExpose({
	setScaleAndTranslate,
});
</script>
