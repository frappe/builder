import useStore from "@/store";
import { posthog } from "@/telemetry";
import Block from "@/utils/block";
import { getBlockCopy, getBlockInstance, throttle, uploadImage } from "@/utils/helpers";
import useComponentStore from "@/utils/useComponentStore";
import { useDropZone } from "@vueuse/core";
import { Ref } from "vue";

const store = useStore();
const componentStore = useComponentStore();

type LayoutDirection = "row" | "column"

export function useCanvasDropZone(
	canvasContainer: Ref<HTMLElement>,
	block: Ref<Block | null>,
	findBlock: (id: string) => Block | null,
) {
	const { isOverDropZone } = useDropZone(canvasContainer, {
		onDrop: async (files, ev) => {
			if (files && files.length) {
				handleFileDrop(files, ev);
			} else {
				const componentName = ev.dataTransfer?.getData("componentName");
				const blockTemplate = ev.dataTransfer?.getData("blockTemplate");
				let { parentBlock, index } = store.dragTarget;
				if (!parentBlock) return;

				if (componentName) {
					await componentStore.loadComponent(componentName);
					const component = componentStore.componentMap.get(componentName) as Block;
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
						parentParentBlock.replaceChild(parentBlock, newBlock);
					} else {
						parentBlock.addChild(newBlock, index);
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
						parentBlock.addChild(newBlock, index);
					}
					posthog.capture("builder_block_template_used", { template: blockTemplate });
				}
			}
		},

		onOver: (files, ev) => {
			if (files && files.length) return;

			const { parentBlock, index, layoutDirection } = findDropTarget(ev);
			if (parentBlock) {
				store.hoveredBlock = parentBlock.blockId;
				updateDropTarget(parentBlock, index, layoutDirection);
			}
		}
	});

	const findDropTarget = (ev: DragEvent) => {
		const element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		const targetElement = element.closest(".__builder_component__") as HTMLElement;

		let parentBlock = block.value;
		let layoutDirection = "column" as LayoutDirection;
		let index = parentBlock?.children.length || 0;

		if (targetElement && targetElement.dataset.blockId) {
			parentBlock = findBlock(targetElement.dataset.blockId) || parentBlock;
			while (parentBlock && !parentBlock.canHaveChildren()) {
				parentBlock = parentBlock.getParentBlock();
			}

			if (parentBlock) {
				const parentElement = document.querySelector(`.__builder_component__[data-block-id="${parentBlock.blockId}"]`) as HTMLElement;
				layoutDirection = getLayoutDirection(parentElement);
				index = findDropIndex(ev, parentElement, layoutDirection);
			}
		}


		return { parentBlock, index, layoutDirection };
	}

	const findDropIndex = (ev: DragEvent, parentElement: HTMLElement, layoutDirection: LayoutDirection): number => {
		const childElements = Array.from(
			parentElement.querySelectorAll(":scope > .__builder_component__"),
		) as HTMLElement[]
		if (childElements.length === 0) return 0

		const mousePos = layoutDirection === "row" ? ev.clientX : ev.clientY

		// Get all child positions
		const childPositions = childElements.map((child, idx) => {
			const rect = child.getBoundingClientRect()
			const midPoint = layoutDirection === "row" ? rect.left + rect.width / 2 : rect.top + rect.height / 2
			return { midPoint, idx }
		})

		// Find the closest child to the mouse position
		let closestIndex = 0
		let minDistance = Infinity

		childPositions.forEach(({ midPoint, idx }) => {
			const distance = Math.abs(midPoint - mousePos)
			if (distance < minDistance) {
				minDistance = distance
				closestIndex = idx
			}
		})

		// Determine if we should insert before or after the closest child
		// if mouse is closer to left/top side of the child, insert before, else after
		return mousePos <= childPositions[closestIndex].midPoint ? closestIndex : closestIndex + 1
	}

	const getLayoutDirection = (element: HTMLElement): LayoutDirection => {
		const style = window.getComputedStyle(element)
		const display = style.display
		if (display === "flex" || display === "inline-flex") {
			return style.flexDirection.includes("row") ? "row" : "column"
		} else if (display === "grid" || display == "inline-grid") {
			return style.gridAutoFlow.includes("row") ? "row" : "column"
		}
		return "column"
	}

	const updateDropTarget = throttle((parentBlock: Block | null, index: number, layoutDirection: LayoutDirection) => {
		// append placeholder component to the dom directly
		// to avoid re-rendering the whole canvas
		const { placeholder } = store.dragTarget
		if (!parentBlock || !placeholder) return
		const newParent = document.querySelector(`.__builder_component__[data-block-id="${parentBlock.blockId}"]`)
		if (!newParent) return

		if (store.dragTarget.parentBlock?.blockId === parentBlock.blockId && store.dragTarget.index === index) return

		// flip placeholder border as per layout direction to avoid shifting elements too much
		if (layoutDirection === "row") {
			placeholder.classList.remove("horizontal-placeholder")
			placeholder.classList.add("vertical-placeholder")
		} else {
			placeholder.classList.remove("vertical-placeholder")
			placeholder.classList.add("horizontal-placeholder")
		}

		// Append the placeholder to the new parent
		newParent.insertBefore(placeholder, newParent.children[index])
		store.dragTarget.parentBlock = parentBlock
		store.dragTarget.index = index
	}, 130)

	const handleFileDrop = (files: File[], ev: DragEvent) => {
		let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
		let parentBlock = block.value as Block | null;
		if (element) {
			if (element.dataset.blockId) {
				parentBlock = findBlock(element.dataset.blockId) || parentBlock;
			}
		}
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

	return { isOverDropZone };
}
