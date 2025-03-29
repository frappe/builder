import type Block from "@/block";
import useBlockTemplateStore from "@/stores/blockTemplateStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import { posthog } from "@/telemetry";
import { getBlockCopy, getBlockInstance, getImageBlock, getVideoBlock, uploadImage } from "@/utils/helpers";
import { useDropZone } from "@vueuse/core";
import { Ref } from "vue";

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();
const blockTemplateStore = useBlockTemplateStore();

type LayoutDirection = "row" | "column";

export function useCanvasDropZone(
	canvasContainer: Ref<HTMLElement>,
	block: Ref<Block | null>,
	findBlock: (id: string) => Block | null,
) {
	const { isOverDropZone } = useDropZone(canvasContainer, {
		onDrop: async (files, ev) => {
			canvasStore.isDropping = true;
			if (files && files.length) {
				handleFileDrop(files, ev);
			} else {
				await handleBlockDrop(ev);
			}
			canvasStore.isDropping = false;
			canvasStore.resetDropTarget();
		},

		onOver: (files, ev) => {
			if (ev.shiftKey) {
				const parentBlock = getBlockToReplace(ev);
				if (parentBlock) {
					canvasStore.activeCanvas?.setHoveredBlock(parentBlock.blockId);
					updateDropTarget(ev, parentBlock, 0, "column");
					canvasStore.removeDropPlaceholder();
				}
			} else {
				const { parentBlock, index, layoutDirection } = findDropTarget(ev);
				if (parentBlock) {
					canvasStore.activeCanvas?.setHoveredBlock(parentBlock.blockId);
					updateDropTarget(ev, parentBlock, index, layoutDirection);
				}
			}
		},
	});

	const getInitialParentBlock = (ev: DragEvent) => {
		const element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		const targetElement = element.closest(".__builder_component__") as HTMLElement;

		// set the hoveredBreakpoint from the target element to show placeholder at the correct breakpoint canvas
		const breakpoint =
			targetElement?.dataset.breakpoint || canvasStore.activeCanvas?.activeBreakpoint || null;
		if (breakpoint !== canvasStore.activeCanvas?.hoveredBreakpoint) {
			canvasStore.activeCanvas?.setHoveredBreakpoint(breakpoint);
		}

		let parentBlock = block.value as Block | null;
		if (targetElement && targetElement.dataset.blockId) {
			parentBlock = findBlock(targetElement.dataset.blockId) || parentBlock;
		}
		return parentBlock;
	};

	const getBlockToReplace = (ev: DragEvent) => {
		let parentBlock = getInitialParentBlock(ev);
		while (parentBlock && parentBlock.isChildOfComponent) {
			parentBlock = parentBlock.getParentBlock();
		}
		return parentBlock;
	};

	const getBlockElement = (block: Block) => {
		const breakpoint =
			canvasStore.activeCanvas?.hoveredBreakpoint || canvasStore.activeCanvas?.activeBreakpoint;
		return document.querySelector(
			`.__builder_component__[data-block-id="${block.blockId}"][data-breakpoint="${breakpoint}"]`,
		) as HTMLElement;
	};

	const findDropTarget = (ev: DragEvent) => {
		if (canvasStore.dropTarget.x === ev.x && canvasStore.dropTarget.y === ev.y) return {};
		let parentBlock = getInitialParentBlock(ev);
		let layoutDirection = "column" as LayoutDirection;
		let index = parentBlock?.children.length || 0;

		while (parentBlock && !parentBlock.canHaveChildren()) {
			parentBlock = parentBlock.getParentBlock();
		}

		if (parentBlock) {
			const parentElement = getBlockElement(parentBlock);
			layoutDirection = getLayoutDirection(parentElement);
			index = findDropIndex(ev, parentElement, layoutDirection);
		}

		return { parentBlock, index, layoutDirection };
	};

	const findDropIndex = (
		ev: DragEvent,
		parentElement: HTMLElement,
		layoutDirection: LayoutDirection,
	): number => {
		const childElements = Array.from(
			parentElement.querySelectorAll(":scope > .__builder_component__, #placeholder"),
		) as HTMLElement[];
		if (childElements.length === 0) return 0;

		const mousePos = layoutDirection === "row" ? ev.clientX : ev.clientY;

		// Get all child positions
		const childPositions = childElements.map((child, idx) => {
			const rect = child.getBoundingClientRect();
			const midPoint = layoutDirection === "row" ? rect.left + rect.width / 2 : rect.top + rect.height / 2;
			return { midPoint, idx };
		});

		// Find the closest child to the mouse position
		let closestIndex = 0;
		let minDistance = Infinity;

		childPositions.forEach(({ midPoint, idx }) => {
			const distance = Math.abs(midPoint - mousePos);
			if (distance < minDistance) {
				minDistance = distance;
				closestIndex = idx;
			}
		});

		// Determine if we should insert before or after the closest child
		// if mouse is closer to left/top side of the child, insert before, else after
		return mousePos <= childPositions[closestIndex].midPoint ? closestIndex : closestIndex + 1;
	};

	const getLayoutDirection = (element: HTMLElement): LayoutDirection => {
		const style = window.getComputedStyle(element);
		const display = style.display;
		if (display === "flex" || display === "inline-flex") {
			return style.flexDirection.includes("row") ? "row" : "column";
		} else if (display === "grid" || display == "inline-grid") {
			return style.gridAutoFlow.includes("row") ? "row" : "column";
		}
		return "column";
	};

	const updateDropTarget = (
		ev: DragEvent,
		parentBlock: Block | null,
		index: number,
		layoutDirection: LayoutDirection,
	) => {
		const placeholder = canvasStore.dropTarget.placeholder;
		if (!placeholder) {
			// File drops don't trigger dragstart so placeholder is never inserted, insert explicitly if not found
			canvasStore.isDragging = true;
			canvasStore.insertDropPlaceholder();
		}

		if (!parentBlock || !placeholder) return;
		const newParent = getBlockElement(parentBlock);
		if (!newParent) return;

		if (
			canvasStore.dropTarget.parentBlock?.blockId === parentBlock.blockId &&
			canvasStore.dropTarget.index === index
		)
			return;

		placeholder.classList.toggle("vertical-placeholder", layoutDirection === "row");
		placeholder.classList.toggle("horizontal-placeholder", layoutDirection === "column");

		// add the placeholder to the new parent
		// exclude placeholder as its going to move with this update
		const children = Array.from(newParent.children).filter((child) => child.id !== "placeholder");
		if (index >= children.length) {
			newParent.appendChild(placeholder);
		} else {
			newParent.insertBefore(placeholder, children[index]);
		}

		canvasStore.dropTarget.parentBlock = parentBlock;
		canvasStore.dropTarget.index = index;
		canvasStore.dropTarget.x = ev.x;
		canvasStore.dropTarget.y = ev.y;
	};

	const handleBlockDrop = async (ev: DragEvent) => {
		let { parentBlock, index } = canvasStore.dropTarget;
		const componentName = ev.dataTransfer?.getData("componentName");
		const blockTemplate = ev.dataTransfer?.getData("blockTemplate");

		if (componentName) {
			await componentStore.loadComponent(componentName);
			const component = componentStore.componentMap.get(componentName) as Block;
			const newBlock = getBlockCopy(component);
			newBlock.extendFromComponent(componentName);
			// if shift key is pressed, replace parent block with new block
			if (ev.shiftKey) {
				if (!parentBlock) return;
				const parentParentBlock = parentBlock.getParentBlock();
				if (!parentParentBlock) return;
				parentParentBlock.replaceChild(parentBlock, newBlock);
			} else {
				if (!parentBlock) return;
				parentBlock.addChild(newBlock, index);
			}
			ev.stopPropagation();
			posthog.capture("builder_component_used");
		} else if (blockTemplate) {
			await blockTemplateStore.fetchBlockTemplate(blockTemplate);
			const newBlock = getBlockInstance(blockTemplateStore.getBlockTemplate(blockTemplate).block, false);
			// if shift key is pressed, replace parent block with new block
			if (ev.shiftKey) {
				parentBlock = getBlockToReplace(ev);
				if (!parentBlock) return;
				const parentParentBlock = parentBlock.getParentBlock();
				if (!parentParentBlock) return;
				const index = parentParentBlock.children.indexOf(parentBlock);
				parentParentBlock.children.splice(index, 1, newBlock);
			} else {
				if (!parentBlock) return;
				parentBlock.addChild(newBlock, index);
			}
			posthog.capture("builder_block_template_used", { template: blockTemplate });
		}
	};

	const handleFileDrop = (files: File[], ev: DragEvent) => {
		let { parentBlock, index } = canvasStore.dropTarget;
		uploadImage(files[0]).then((fileDoc: { fileURL: string; fileName: string }) => {
			if (!parentBlock) return;

			if (fileDoc.fileName.match(/\.(mp4|webm|ogg|mov)$/)) {
				if (parentBlock.isVideo()) {
					parentBlock.setAttribute("src", fileDoc.fileURL);
				} else {
					parentBlock.addChild(getVideoBlock(fileDoc.fileURL), index);
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
				const imageBlock = getImageBlock(fileDoc.fileURL, fileDoc.fileName);
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
				parentBlock.addChild(getImageBlock(fileDoc.fileURL, fileDoc.fileName), index);
				posthog.capture("builder_image_uploaded", {
					type: "new-image",
				});
			}
		});
	};

	return { isOverDropZone };
}
