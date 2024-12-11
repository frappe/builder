<template>
	<div ref="canvasContainer" @click="handleClick">
		<slot name="header"></slot>
		<div class="overlay absolute" id="overlay" ref="overlay" />
		<Transition name="fade">
			<div
				class="absolute bottom-0 left-0 right-0 top-0 z-[19] grid w-full place-items-center bg-surface-gray-1 p-10 text-ink-gray-5"
				v-show="store.settingPage">
				<LoadingIcon></LoadingIcon>
			</div>
		</Transition>
		<BlockSnapGuides></BlockSnapGuides>
		<div
			v-if="isOverDropZone"
			class="pointer-events-none absolute bottom-0 left-0 right-0 top-0 z-30 bg-cyan-300 opacity-20"></div>
		<div
			class="fixed flex gap-40"
			ref="canvas"
			:style="{
				transformOrigin: 'top center',
				transform: `scale(${canvasProps.scale}) translate(${canvasProps.translateX}px, ${canvasProps.translateY}px)`,
			}">
			<div class="absolute right-0 top-[-60px] flex rounded-md bg-surface-white px-3">
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
							'text-ink-gray-8': breakpoint.visible,
							'text-ink-gray-3': !breakpoint.visible,
						}" />
				</div>
			</div>
			<div
				class="canvas relative flex h-full rounded-md bg-surface-white shadow-2xl"
				:style="{
					...canvasStyles,
					background: canvasProps.background,
					width: `${breakpoint.width}px`,
				}"
				v-for="breakpoint in visibleBreakpoints"
				:key="breakpoint.device">
				<div
					class="cursor absolute left-0 select-none text-3xl text-gray-700 dark:text-zinc-300"
					:style="{
						fontSize: `calc(${12}px * 1/${canvasProps.scale})`,
						top: `calc(${-20}px * 1/${canvasProps.scale})`,
					}"
					v-show="!canvasProps.scaling && !canvasProps.panning"
					@click="store.activeBreakpoint = breakpoint.device">
					{{ breakpoint.displayName }}
				</div>
				<BuilderBlock
					class="h-full min-h-[inherit]"
					:block="block"
					:key="block.blockId"
					v-if="showBlocks"
					:breakpoint="breakpoint.device"
					:data="store.pageData" />
			</div>
		</div>
		<div
			class="fixed bottom-12 left-[50%] z-40 flex translate-x-[-50%] cursor-default items-center justify-center gap-2 rounded-lg bg-surface-white px-3 py-2 text-center text-sm font-semibold text-gray-600 shadow-md dark:text-zinc-400"
			v-show="!canvasProps.panning">
			{{ Math.round(canvasProps.scale * 100) + "%" }}
			<div class="ml-2 cursor-pointer" @click="setScaleAndTranslate">
				<FitScreenIcon />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import LoadingIcon from "@/components/Icons/Loading.vue";
import { posthog } from "@/telemetry";
import Block from "@/utils/block";
import getBlockTemplate from "@/utils/blockTemplate";
import {
	addPxToNumber,
	getBlockCopy,
	getBlockInstance,
	getNumberFromPx,
	isTargetEditable,
	uploadImage,
} from "@/utils/helpers";
import { useCanvasHistory } from "@/utils/useCanvasHistory";
import { clamp, useDropZone, useElementBounding, useEventListener } from "@vueuse/core";
import { FeatherIcon } from "frappe-ui";
import { Ref, computed, nextTick, onMounted, provide, reactive, ref, watch } from "vue";
import { toast } from "vue-sonner";
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
const isDirty = ref(false);
let selectionTrail = [] as string[];

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

const canvasHistory = ref(null) as Ref<ReturnType<typeof useCanvasHistory>> | Ref<null>;

provide("canvasProps", canvasProps);

onMounted(() => {
	canvasProps.overlayElement = overlay.value;
	setupHistory();
	setEvents();
});

function setupHistory() {
	canvasHistory.value = useCanvasHistory(block, selectedBlockIds) as ReturnType<typeof useCanvasHistory>;
}

const { isOverDropZone } = useDropZone(canvasContainer, {
	onDrop: async (files, ev) => {
		let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		let parentBlock = block.value as Block | null;
		if (element) {
			if (element.dataset.blockId) {
				parentBlock = findBlock(element.dataset.blockId) || parentBlock;
			}
		}
		const componentName = ev.dataTransfer?.getData("componentName");
		const blockTemplate = ev.dataTransfer?.getData("blockTemplate");
		if (componentName) {
			await store.loadComponent(componentName);
			const component = store.componentMap.get(componentName) as Block;
			const newBlock = getBlockCopy(component);
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
			posthog.capture("builder_component_used");
		} else if (blockTemplate) {
			await store.fetchBlockTemplate(blockTemplate);
			const newBlock = getBlockInstance(store.getBlockTemplate(blockTemplate).block, false);
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
			posthog.capture("builder_block_template_used", { template: blockTemplate });
		} else if (files && files.length) {
			uploadImage(files[0]).then((fileDoc: { fileURL: string; fileName: string }) => {
				if (!parentBlock) return;

				if (fileDoc.fileName.match(/\.(mp4|webm|ogg|mov)$/)) {
					if (parentBlock.isVideo()) {
						parentBlock.setAttribute("src", fileDoc.fileURL);
					} else {
						while (parentBlock && !parentBlock.canHaveChildren()) {
							parentBlock = parentBlock.getParentBlock() as Block;
						}
						parentBlock.addChild(store.getVideoBlock(fileDoc.fileURL));
					}
					posthog.capture("builder_video_uploaded");
					return;
				}

				if (parentBlock.isImage()) {
					parentBlock.setAttribute("src", fileDoc.fileURL);
					posthog.capture("builder_image_uploaded", {
						type: "image-replace",
					});
				} else if (parentBlock.isSVG()) {
					const imageBlock = store.getImageBlock(fileDoc.fileURL, fileDoc.fileName);
					const parentParentBlock = parentBlock.getParentBlock();
					parentParentBlock?.replaceChild(parentBlock, getBlockInstance(imageBlock));
					posthog.capture("builder_image_uploaded", {
						type: "svg-replace",
					});
				} else if (parentBlock.isContainer() && ev.shiftKey) {
					parentBlock.setStyle("background", `url(${fileDoc.fileURL})`);
					posthog.capture("builder_image_uploaded", {
						type: "background",
					});
				} else {
					while (parentBlock && !parentBlock.canHaveChildren()) {
						parentBlock = parentBlock.getParentBlock() as Block;
					}
					parentBlock.addChild(store.getImageBlock(fileDoc.fileURL, fileDoc.fileName));
					posthog.capture("builder_image_uploaded", {
						type: "new-image",
					});
				}
			});
		}
	},
});

const visibleBreakpoints = computed(() => {
	return canvasProps.breakpoints.filter(
		(breakpoint) => breakpoint.visible || breakpoint.device === "desktop",
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
			const pauseId = canvasHistory.value?.pause();
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
				`.canvas [data-block-id="${parentBlock.blockId}"]`,
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
					const setFullWidth = width === parentWidth;
					childBlock.setBaseStyle("width", setFullWidth ? "100%" : addPxToNumber(width));
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
						pauseId && canvasHistory.value?.resume(pauseId, true);
						store.editableBlock = childBlock;
						return;
					}
					if (parentBlock.isGrid()) {
						childBlock.setStyle("width", "auto");
						childBlock.setStyle("height", "100%");
					} else {
						if (getNumberFromPx(childBlock.getStyle("width")) < 100) {
							childBlock.setBaseStyle("width", "100%");
						}
						if (getNumberFromPx(childBlock.getStyle("height")) < 100) {
							childBlock.setBaseStyle("height", "200px");
						}
					}
					pauseId && canvasHistory.value?.resume(pauseId, true);
				},
				{ once: true },
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
				{ once: true },
			);
			ev.stopPropagation();
			ev.preventDefault();
		}
	});

	useEventListener(document, "keydown", (ev: KeyboardEvent) => {
		if (isTargetEditable(ev) || selectedBlocks.value.length !== 1) return;

		const selectedBlock = selectedBlocks.value[0];

		const selectBlock = (block: Block | null) => {
			if (block) store.selectBlock(block, null, true, true);
			return !!block;
		};

		const selectSibling = (direction: "previous" | "next", fallback: () => void) => {
			selectBlock(selectedBlock.getSiblingBlock(direction)) || fallback();
		};

		const selectParent = () => selectBlock(selectedBlock.getParentBlock());

		const selectFirstChild = () => selectBlock(selectedBlock.children[0]);

		const selectNextSiblingOrParent = () => {
			let sibling = selectedBlock.getSiblingBlock("next");
			let parentBlock = selectedBlock.getParentBlock();
			while (!sibling && parentBlock) {
				sibling = parentBlock.getSiblingBlock("next");
				parentBlock = parentBlock.getParentBlock();
			}
			selectBlock(sibling);
		};

		const selectLastChildInTree = (block: Block) => {
			let currentBlock = block;
			while (store.activeLayers?.isExpandedInTree(currentBlock)) {
				const lastChild = currentBlock.getLastChild() as Block;
				if (!lastChild) break;
				currentBlock = lastChild;
			}
			selectBlock(currentBlock);
		};

		switch (ev.key) {
			case "ArrowLeft":
				store.activeLayers?.isExpandedInTree(selectedBlock)
					? store.activeLayers.toggleExpanded(selectedBlock)
					: selectSibling("previous", selectParent);
				break;
			case "ArrowRight":
				selectedBlock.hasChildren() && selectedBlock.isVisible()
					? (store.activeLayers?.toggleExpanded(selectedBlock), selectFirstChild())
					: selectNextSiblingOrParent();
				break;
			case "ArrowUp":
				selectBlock(selectedBlock.getSiblingBlock("previous"))
					? selectLastChildInTree(selectedBlock.getSiblingBlock("previous") as Block)
					: selectParent();
				break;
			case "ArrowDown":
				store.activeLayers?.isExpandedInTree(selectedBlock) &&
				selectedBlock.hasChildren() &&
				selectedBlock.isVisible()
					? selectFirstChild()
					: selectNextSiblingOrParent();
				break;
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
	const paddingY = 200;

	await nextTick();
	canvasBound.update();
	const containerWidth = containerBound.width;
	const canvasWidth = canvasBound.width / canvasProps.scale;

	canvasProps.scale = containerWidth / (canvasWidth + paddingX * 2);

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
	setPanAndZoom(canvasEl, canvasContainerEl, canvasProps);
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
	},
);

watch(
	() => store.mode,
	(newValue, oldValue) => {
		store.lastMode = oldValue;
		toggleMode(store.mode);
	},
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
			toggleDirty(false);
		});
	}
};

const selectedBlockIds = ref([]) as Ref<string[]>;
const selectedBlocks = computed(() => {
	return selectedBlockIds.value.map((id) => findBlock(id)).filter((b) => b) as Block[];
}) as Ref<Block[]>;

const isSelected = (block: Block) => {
	return selectedBlockIds.value.includes(block.blockId);
};

let maintainTrail = false;

const selectBlock = (_block: Block, multiSelect = false) => {
	if (multiSelect) {
		selectedBlockIds.value.push(_block.blockId);
	} else {
		selectedBlockIds.value.splice(0, selectedBlockIds.value.length, _block.blockId);
	}
	if (!maintainTrail) {
		selectionTrail = [];
	}
};

const toggleBlockSelection = (_block: Block) => {
	if (isSelected(_block)) {
		selectedBlockIds.value.splice(selectedBlockIds.value.indexOf(_block.blockId), 1);
	} else {
		selectBlock(_block, true);
	}
};

const selectBlockRange = (newSelectedBlock: Block) => {
	const lastSelectedBlockId = selectedBlockIds.value[selectedBlockIds.value.length - 1];
	const lastSelectedBlock = findBlock(lastSelectedBlockId);
	const lastSelectedBlockParent = lastSelectedBlock?.parentBlock;
	if (!lastSelectedBlock || !lastSelectedBlockParent) {
		newSelectedBlock.selectBlock();
		return;
	}
	const lastSelectedBlockIndex = lastSelectedBlock.parentBlock?.children.indexOf(lastSelectedBlock);
	const newSelectedBlockIndex = newSelectedBlock.parentBlock?.children.indexOf(newSelectedBlock);
	const newSelectedBlockParent = newSelectedBlock.parentBlock;
	if (lastSelectedBlockIndex === undefined || newSelectedBlockIndex === undefined) {
		return;
	}
	const start = Math.min(lastSelectedBlockIndex, newSelectedBlockIndex);
	const end = Math.max(lastSelectedBlockIndex, newSelectedBlockIndex);
	if (lastSelectedBlockParent === newSelectedBlockParent) {
		const blocks = lastSelectedBlockParent.children.slice(start, end + 1);
		selectedBlockIds.value = selectedBlockIds.value.concat(...blocks.map((b) => b.blockId));
		selectedBlockIds.value = Array.from(new Set(selectedBlockIds.value));
	}
};

const clearSelection = () => {
	selectedBlockIds.value = [];
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

const removeBlock = (block: Block) => {
	if (block.blockId === "root") {
		toast.warning("Warning", {
			description: "Cannot delete root block",
		});
		return;
	}
	if (block.isChildOfComponentBlock()) {
		toast.warning("Warning", {
			description: "Cannot delete block inside component",
		});
		return;
	}
	const parentBlock = block.parentBlock;
	if (!parentBlock) {
		return;
	}
	const index = parentBlock.children.indexOf(block);
	parentBlock.removeChild(block);
	nextTick(() => {
		if (parentBlock.children.length) {
			const nextSibling = parentBlock.children[index] || parentBlock.children[index - 1];
			if (nextSibling) {
				selectBlock(nextSibling);
			}
		}
	});
};

watch(
	() => block,
	() => {
		toggleDirty(true);
	},
	{
		deep: true,
	},
);

const toggleDirty = (dirty: boolean | null = null) => {
	if (dirty === null) {
		isDirty.value = !isDirty.value;
	} else {
		isDirty.value = dirty;
	}
};

const scrollBlockIntoView = async (blockToFocus: Block) => {
	// wait for editor to render
	await new Promise((resolve) => setTimeout(resolve, 100));
	await nextTick();
	if (
		!canvasContainer.value ||
		!canvas.value ||
		blockToFocus.isRoot() ||
		!blockToFocus.isVisible() ||
		blockToFocus.getParentBlock()?.isSVG()
	) {
		return;
	}
	const container = canvasContainer.value as HTMLElement;
	const containerRect = container.getBoundingClientRect();
	const selectedBlock = document.body.querySelector(
		`.editor[data-block-id="${blockToFocus.blockId}"][selected=true]`,
	) as HTMLElement;
	if (!selectedBlock) {
		return;
	}
	const blockRect = reactive(useElementBounding(selectedBlock));
	// check if block is in view
	if (
		blockRect.top >= containerRect.top &&
		blockRect.bottom <= containerRect.bottom &&
		blockRect.left >= containerRect.left &&
		blockRect.right <= containerRect.right
	) {
		return;
	}

	let padding = 80;
	let paddingBottom = 200;
	const blockWidth = blockRect.width + padding * 2;
	const containerBound = container.getBoundingClientRect();
	const blockHeight = blockRect.height + padding + paddingBottom;

	const scaleX = containerBound.width / blockWidth;
	const scaleY = containerBound.height / blockHeight;
	const newScale = Math.min(scaleX, scaleY);

	const scaleDiff = canvasProps.scale - canvasProps.scale * newScale;
	if (scaleDiff > 0.2) {
		return;
	}

	if (newScale < 1) {
		canvasProps.scale = canvasProps.scale * newScale;
		await new Promise((resolve) => setTimeout(resolve, 100));
		await nextTick();
		blockRect.update();
	}

	padding = padding * canvasProps.scale;
	paddingBottom = paddingBottom * canvasProps.scale;

	// slide in block from the closest edge of the container
	const diffTop = containerRect.top - blockRect.top + padding;
	const diffBottom = blockRect.bottom - containerRect.bottom + paddingBottom;
	const diffLeft = containerRect.left - blockRect.left + padding;
	const diffRight = blockRect.right - containerRect.right + padding;

	if (diffTop > 0) {
		canvasProps.translateY += diffTop / canvasProps.scale;
	} else if (diffBottom > 0) {
		canvasProps.translateY -= diffBottom / canvasProps.scale;
	}

	if (diffLeft > 0) {
		canvasProps.translateX += diffLeft / canvasProps.scale;
	} else if (diffRight > 0) {
		canvasProps.translateX -= diffRight / canvasProps.scale;
	}
};

defineExpose({
	setScaleAndTranslate,
	resetZoom,
	moveCanvas,
	zoomIn,
	zoomOut,
	history: canvasHistory,
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
	findBlock,
	isDirty,
	toggleDirty,
	scrollBlockIntoView,
	removeBlock,
	selectBlockRange,
});
</script>
