<template>
	<div
		ref="canvasContainer"
		:style="{
			left: `${store.builderLayout.leftPanelWidth}px`,
			right: `${store.builderLayout.rightPanelWidth}px`,
		}">
		<div class="overlay absolute" id="overlay" ref="overlay" />
		<BlockSnapGuides />
		<div
			v-if="isOverDropZone"
			class="pointer-events-none absolute bottom-0 left-0 right-0 top-0 z-30 bg-cyan-300 opacity-20"></div>
		<div
			class="fixed flex will-change-transform"
			ref="canvas"
			:style="{
				transformStyle: 'preserve-3d',
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
				class="canvas relative ml-20 flex h-full rounded-md bg-white"
				:style="{
					background: canvasProps.background,
					width: `${breakpoint.width}px`,
					...canvasStyles,
				}"
				v-for="breakpoint in visibleBreakpoints"
				:key="breakpoint.device">
				<BuilderBlock :block="block" v-if="showBlocks" :breakpoint="breakpoint.device" />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { useDebouncedRefHistory, useElementBounding, useDropZone } from "@vueuse/core";
import { FeatherIcon, toast } from "frappe-ui";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import BuilderBlock from "./BuilderBlock.vue";
import { FileUploadHandler } from "frappe-ui";
import { provide } from "vue";

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
		type: Object,
		default: () => ({}),
	},
	canvasStyles: {
		type: Object,
		default: () => ({}),
	},
});

provide("canvasProps", props.canvasProps);

const { isOverDropZone } = useDropZone(canvasContainer, {
	onDrop: (files, ev) => {
		let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		let block = props.block;
		if (element) {
			if (element.dataset.blockId) {
				block = store.findBlock(element.dataset.blockId) || block;
			}
		}
		if (files && files.length) {
			const uploader = new FileUploadHandler();
			uploader
				.upload(files[0], {
					private: false,
				})
				.then((fileDoc: { file_url: string }) => {
					const url = encodeURI(window.location.origin + fileDoc.file_url);
					if (block.isImage()) {
						block.setAttribute("src", url);
					} else {
						block.addChild(store.getImageBlock(url));
					}
				});
		}
	},
});

const clearSelectedComponent = () => {
	store.builderState.selectedBlocks = [];
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
	if (
		e.key === "Backspace" &&
		store.builderState.selectedBlocks.length &&
		!target.closest(".__builder_component__") &&
		!target.getAttribute("contenteditable")
	) {
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
					return true;
				} else if (block.children) {
					return findBlockAndRemove(block.children, blockId);
				}
			});
		}
		for (const block of store.builderState.selectedBlocks) {
			findBlockAndRemove(store.builderState.blocks, block.blockId);
		}
		clearSelectedComponent();
	}

	if (e.key === "Escape") {
		store.editingComponent = null;
		clearSelectedComponent();
	}

	// handle arrow keys
	if (e.key.startsWith("Arrow") && store.builderState.selectedBlocks.length) {
		const key = e.key.replace("Arrow", "").toLowerCase() as "up" | "down" | "left" | "right";
		for (const block of store.builderState.selectedBlocks) {
			block.move(key);
		}
	}
});

const containerBound = reactive(useElementBounding(canvasContainer));
const canvasBound = reactive(useElementBounding(canvas));

const setScaleAndTranslate = async () => {
	const paddingX = 300;
	const paddingY = 400;
	props.canvasProps.scale = 1;
	props.canvasProps.translateX = 0;
	props.canvasProps.translateY = 0;

	await nextTick();
	canvasBound.update();
	const containerWidth = containerBound.width;
	const containerHeight = containerBound.height;
	props.canvasProps.initialScale = props.canvasProps.scale = Math.min(
		containerWidth / (canvasBound.width + paddingX * 2),
		containerHeight / (canvasBound.height + paddingY * 2)
	);

	await nextTick();
	const scale = props.canvasProps.scale;
	canvasBound.update();
	const diffY = containerBound.top - canvasBound.top + paddingY * scale;
	if (diffY !== 0) {
		props.canvasProps.initialTranslateY = props.canvasProps.translateY = diffY / scale;
	}
};

onMounted(() => {
	const canvasContainerEl = canvasContainer.value as unknown as HTMLElement;
	const canvasEl = canvas.value as unknown as HTMLElement;
	setPanAndZoom(props.canvasProps, canvasEl, canvasContainerEl);
	const { builderState } = storeToRefs(store);
	const { undo, redo, canUndo, canRedo } = useDebouncedRefHistory(builderState, {
		capacity: 100,
		deep: true,
		clone: (obj) => {
			let newObj = Object.assign({}, obj);
			newObj.blocks = obj.blocks.map((val) => store.getBlockCopy(val, true));
			if (obj.selectedBlocks) {
				newObj.selectedBlocks = obj.selectedBlocks.map((val) => {
					return store.findBlock(val.blockId, newObj.blocks);
				}) as Array<Block>;
			}
			return newObj;
		},
		debounce: 200,
	});

	document.addEventListener("keydown", (e) => {
		const target = e.target as HTMLElement;
		if (
			target.tagName === "INPUT" ||
			target.tagName === "TEXTAREA" ||
			target.getAttribute("contenteditable")
		) {
			return;
		}
		if (e.key === "z" && e.metaKey && !e.shiftKey && canUndo.value) {
			undo();
			e.preventDefault();
		}
		if (e.key === "z" && e.shiftKey && e.metaKey && canRedo.value) {
			redo();
			e.preventDefault();
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
	showBlocks.value = true;
	setTimeout(setScaleAndTranslate, 500);
});

watch(store.deviceBreakpoints, setScaleAndTranslate, { deep: true });
</script>
