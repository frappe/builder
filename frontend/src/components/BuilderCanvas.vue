<template>
	<div ref="canvasContainer" @click="handleClick">
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
					v-for="breakpoint in canvasProps.breakpoints"
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
					v-show="!canvasProps.scaling && !canvasProps.panning"
					@click="store.activeBreakpoint = breakpoint.device">
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
				<FitScreenIcon />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import Block from "@/utils/block";
import getBlockTemplate from "@/utils/blockTemplate";
import { addPxToNumber, getBlockCopy, getNumberFromPx } from "@/utils/helpers";
import {
	UseRefHistoryReturn,
	clamp,
	useDebouncedRefHistory,
	useDropZone,
	useElementBounding,
	useEventListener,
} from "@vueuse/core";
import { FeatherIcon } from "frappe-ui";
import { Ref, computed, nextTick, onMounted, provide, reactive, ref, watch } from "vue";
import useStore from "../store";
import setPanAndZoom from "../utils/panAndZoom";
import BlockSnapGuides from "./BlockSnapGuides.vue";
import BuilderBlock from "./BuilderBlock.vue";
import FitScreenIcon from "./Icons/FitScreen.vue";

const store = useStore();
const canvasContainer = ref(null);
const canvas = ref(null);
const showBlocks = ref(false);
const overlay = ref(null);

const props = defineProps({
	blockData: {
		type: Block,
		default: false,
	},
	canvasStyles: {
		type: Object,
		default: () => ({}),
	},
});

// clone props.block into canvas data to avoid mutating them
const block = ref(getBlockCopy(props.blockData, true)) as Ref<Block>;

const canvasProps = reactive({
	overlayElement: null,
	background: "#fff",
	scale: 1,
	translateX: 0,
	translateY: 0,
	settingCanvas: true,
	scaling: false,
	panning: false,
	breakpoints: [
		{
			icon: "monitor",
			device: "desktop",
			displayName: "Desktop",
			width: 1400,
			visible: true,
		},
		{
			icon: "tablet",
			device: "tablet",
			displayName: "Tablet",
			width: 800,
			visible: false,
		},
		{
			icon: "smartphone",
			device: "mobile",
			displayName: "Mobile",
			width: 420,
			visible: false,
		},
	],
});

const canvasHistory = ref(null) as Ref<UseRefHistoryReturn<{}, {}>> | Ref<null>;

provide("canvasProps", canvasProps);

onMounted(() => {
	canvasProps.overlayElement = overlay.value;
	setupHistory();
	setEvents();
});

function setupHistory() {
	canvasHistory.value = useDebouncedRefHistory(block, {
		capacity: 200,
		deep: true,
		debounce: 200,
		clone: (obj) => {
			return getBlockCopy(obj, true);
		},
	});
}

const { isOverDropZone } = useDropZone(canvasContainer, {
	onDrop: (files, ev) => {
		let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		let parentBlock = block.value as Block | null;
		if (element) {
			if (element.dataset.blockId) {
				parentBlock = findBlock(element.dataset.blockId) || parentBlock;
			}
		}
		let componentName = ev.dataTransfer?.getData("componentName");
		if (componentName) {
			const newBlock = getBlockCopy(webComponent.getRow(componentName).block, true);
			newBlock.extendFromComponent(componentName);
			// if shift key is pressed, replace parent block with new block
			if (ev.shiftKey) {
				while (parentBlock && parentBlock.isChildOfComponent) {
					parentBlock = parentBlock.getParentBlock();
				}
				if (!parentBlock) return;
				const parentParentBlock = parentBlock.getParentBlock();
				if (!parentParentBlock) return;
				const index = parentParentBlock.children.indexOf(parentBlock);
				parentParentBlock.children.splice(index, 1, newBlock);
			} else {
				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock();
				}
				if (!parentBlock) return;
				parentBlock.addChild(newBlock);
			}
			ev.stopPropagation();
		} else if (files && files.length) {
			store.uploadFile(files[0]).then((fileDoc: { fileURL: string; fileName: string }) => {
				if (!parentBlock) return;
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
	return canvasProps.breakpoints.filter(
		(breakpoint) => breakpoint.visible || breakpoint.device === "desktop"
	);
});

function setEvents() {
	const container = document.body.querySelector(".canvas-container") as HTMLElement;
	let counter = 0;
	useEventListener(container, "mousedown", (ev: MouseEvent) => {
		if (store.mode === "move") {
			return;
		}
		const initialX = ev.clientX;
		const initialY = ev.clientY;
		if (store.mode === "select") {
			return;
		} else {
			canvasHistory.value?.pause();
			ev.stopPropagation();
			let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
			let block = getFirstBlock();
			if (element) {
				if (element.dataset.blockId) {
					block = findBlock(element.dataset.blockId) || block;
				}
			}
			let parentBlock = getFirstBlock();
			if (element.dataset.blockId) {
				parentBlock = findBlock(element.dataset.blockId) || parentBlock;
				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock() || getFirstBlock();
				}
			}
			const child = getBlockTemplate(store.mode);
			const parentElement = document.body.querySelector(
				`.canvas [data-block-id="${parentBlock.blockId}"]`
			) as HTMLElement;
			const parentOldPosition = parentBlock.getStyle("position");
			if (parentOldPosition === "static" || parentOldPosition === "inherit" || !parentOldPosition) {
				parentBlock.setBaseStyle("position", "relative");
			}
			const parentElementBounds = parentElement.getBoundingClientRect();
			let x = (ev.x - parentElementBounds.left) / canvasProps.scale;
			let y = (ev.y - parentElementBounds.top) / canvasProps.scale;
			const parentWidth = getNumberFromPx(getComputedStyle(parentElement).width);
			const parentHeight = getNumberFromPx(getComputedStyle(parentElement).height);

			const childBlock = parentBlock.addChild(child);
			childBlock.setBaseStyle("position", "absolute");
			childBlock.setBaseStyle("top", addPxToNumber(y));
			childBlock.setBaseStyle("left", addPxToNumber(x));
			if (store.mode === "container" || store.mode === "repeater") {
				const colors = ["#ededed", "#e2e2e2", "#c7c7c7"];
				childBlock.setBaseStyle("background", colors[counter % colors.length]);
				counter++;
			}

			const mouseMoveHandler = (mouseMoveEvent: MouseEvent) => {
				if (store.mode === "text") {
					return;
				} else {
					mouseMoveEvent.preventDefault();
					let width = (mouseMoveEvent.clientX - initialX) / canvasProps.scale;
					let height = (mouseMoveEvent.clientY - initialY) / canvasProps.scale;
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
					parentBlock.setBaseStyle("position", parentOldPosition || "static");
					childBlock.setBaseStyle("position", "static");
					childBlock.setBaseStyle("top", "auto");
					childBlock.setBaseStyle("left", "auto");
					setTimeout(() => {
						store.mode = "select";
					}, 50);
					if (store.mode === "text") {
						canvasHistory.value?.resume(true);
						return;
					}
					if (getNumberFromPx(childBlock.getStyle("width")) < 100) {
						childBlock.setBaseStyle("width", "100%");
					}
					if (getNumberFromPx(childBlock.getStyle("height")) < 100) {
						childBlock.setBaseStyle("height", "200px");
					}
					canvasHistory.value?.resume(true);
				},
				{ once: true }
			);
		}
	});

	useEventListener(container, "mousedown", (ev: MouseEvent) => {
		if (store.mode === "move") {
			container.style.cursor = "grabbing";
			const initialX = ev.clientX;
			const initialY = ev.clientY;
			const initialTranslateX = canvasProps.translateX;
			const initialTranslateY = canvasProps.translateY;
			const mouseMoveHandler = (mouseMoveEvent: MouseEvent) => {
				mouseMoveEvent.preventDefault();
				const diffX = (mouseMoveEvent.clientX - initialX) / canvasProps.scale;
				const diffY = (mouseMoveEvent.clientY - initialY) / canvasProps.scale;
				canvasProps.translateX = initialTranslateX + diffX;
				canvasProps.translateY = initialTranslateY + diffY;
			};
			useEventListener(document, "mousemove", mouseMoveHandler);
			useEventListener(
				document,
				"mouseup",
				() => {
					document.removeEventListener("mousemove", mouseMoveHandler);
					container.style.cursor = "grab";
				},
				{ once: true }
			);
			ev.stopPropagation();
			ev.preventDefault();
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

	const canvasWidth = canvasBound.width / canvasProps.scale;
	const canvasHeight = canvasBound.height / canvasProps.scale;

	canvasProps.scale = Math.min(
		containerWidth / (canvasWidth + paddingX * 2),
		containerHeight / (canvasHeight + paddingY * 2)
	);

	canvasProps.translateX = 0;
	canvasProps.translateY = 0;
	await nextTick();
	const scale = canvasProps.scale;
	canvasBound.update();
	const diffY = containerBound.top - canvasBound.top + paddingY * scale;
	if (diffY !== 0) {
		canvasProps.translateY = diffY / scale;
	}
	canvasProps.settingCanvas = false;
};

onMounted(() => {
	setScaleAndTranslate();
	const canvasContainerEl = canvasContainer.value as unknown as HTMLElement;
	const canvasEl = canvas.value as unknown as HTMLElement;
	setPanAndZoom(canvasProps, canvasEl, canvasContainerEl);
	showBlocks.value = true;
});

const resetZoom = () => {
	canvasProps.scale = 1;
	canvasProps.translateX = 0;
	canvasProps.translateY = 0;
};

const moveCanvas = (direction: "up" | "down" | "right" | "left") => {
	if (direction === "up") {
		canvasProps.translateY -= 20;
	} else if (direction === "down") {
		canvasProps.translateY += 20;
	} else if (direction === "right") {
		canvasProps.translateX += 20;
	} else if (direction === "left") {
		canvasProps.translateX -= 20;
	}
};

const zoomIn = () => {
	canvasProps.scale = Math.min(canvasProps.scale + 0.1, 10);
};

const zoomOut = () => {
	canvasProps.scale = Math.max(canvasProps.scale - 0.1, 0.1);
};

watch(
	() => canvasProps.breakpoints.map((b) => b.visible),
	() => {
		if (canvasProps.settingCanvas) {
			return;
		}
		setScaleAndTranslate();
	}
);

watch(
	() => store.mode,
	(newValue, oldValue) => {
		store.lastMode = oldValue;
		toggleMode(store.mode);
	}
);

function toggleMode(mode: BuilderMode) {
	if (!canvasContainer.value) return;
	const container = canvasContainer.value as HTMLElement;
	if (mode === "text") {
		container.style.cursor = "text";
	} else if (["container", "image", "repeater"].includes(mode)) {
		container.style.cursor = "crosshair";
	} else if (mode === "move") {
		container.style.cursor = "grab";
	} else {
		container.style.cursor = "default";
	}
}

const handleClick = (ev: MouseEvent) => {
	const target = document.elementFromPoint(ev.clientX, ev.clientY);
	// hack to ensure if click is on canvas-container
	// TODO: Still clears selection if space handlers are dragged over canvas-container
	if (target?.classList.contains("canvas-container")) {
		clearSelection();
	}
};

const clearCanvas = () => {
	block.value = store.getRootBlock();
};

const getFirstBlock = () => {
	return block.value;
};

const setRootBlock = (newBlock: Block, resetCanvas = false) => {
	block.value = newBlock;
	if (canvasHistory.value) {
		canvasHistory.value.dispose();
		setupHistory();
	}
	if (resetCanvas) {
		nextTick(() => {
			setScaleAndTranslate();
		});
	}
};

const selectedBlockIds = ref([]) as Ref<string[]>;
const selectedBlocks = computed(() => {
	return selectedBlockIds.value.map((id) => findBlock(id));
}) as Ref<Block[]>;

const isSelected = (block: Block) => {
	return selectedBlockIds.value.includes(block.blockId);
};

const selectBlock = (_block: Block, multiSelect = false) => {
	if (isSelected(_block)) {
		return;
	}
	if (multiSelect) {
		selectedBlockIds.value.push(_block.blockId);
	} else {
		selectedBlockIds.value.splice(0, selectedBlockIds.value.length, _block.blockId);
	}
};

const toggleBlockSelection = (_block: Block) => {
	if (isSelected(_block)) {
		selectedBlockIds.value.splice(selectedBlockIds.value.indexOf(_block.blockId), 1);
	} else {
		selectBlock(_block, true);
	}
};

const clearSelection = () => {
	selectedBlockIds.value = [];
};

// findParentBlock(blockId: string, blocks?: Array<Block>): Block | null {
// 			if (!blocks) {
// 				const firstBlock = this.activeCanvas?.getFirstBlock() as Block;
// 				if (!firstBlock) {
// 					return null;
// 				}
// 				blocks = [firstBlock];
// 			}
// 			for (const block of blocks) {
// 				if (block.children) {
// 					for (const child of block.children) {
// 						if (child.blockId === blockId) {
// 							return block;
// 						}
// 					}
// 					const found = this.findParentBlock(blockId, block.children);
// 					if (found) {
// 						return found;
// 					}
// 				}
// 			}
// 			return null;
// 		},

const findParentBlock = (blockId: string, blocks?: Block[]): Block | null => {
	if (!blocks) {
		const firstBlock = getFirstBlock();
		if (!firstBlock) {
			return null;
		}
		blocks = [firstBlock];
	}
	for (const block of blocks) {
		if (block.children) {
			for (const child of block.children) {
				if (child.blockId === blockId) {
					return block;
				}
			}
			const found = findParentBlock(blockId, block.children);
			if (found) {
				return found;
			}
		}
	}
	return null;
};

const findBlock = (blockId: string, blocks?: Block[]): Block | null => {
	if (!blocks) {
		blocks = [getFirstBlock()];
	}
	for (const block of blocks) {
		if (block.blockId === blockId) {
			return block;
		}
		if (block.children) {
			const found = findBlock(blockId, block.children);
			if (found) {
				return found;
			}
		}
	}
	return null;
};

defineExpose({
	setScaleAndTranslate,
	resetZoom,
	moveCanvas,
	zoomIn,
	zoomOut,
	history: canvasHistory as Ref<UseRefHistoryReturn<{}, {}>>,
	clearCanvas,
	getFirstBlock,
	block,
	setRootBlock,
	canvasProps,
	selectBlock,
	toggleBlockSelection,
	selectedBlocks,
	clearSelection,
	isSelected,
	selectedBlockIds,
	findParentBlock,
	findBlock,
});
</script>
