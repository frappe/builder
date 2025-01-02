import useStore from "@/store";
import { posthog } from "@/telemetry";
import Block from "@/utils/block";
import { getBlockCopy, getBlockInstance, uploadImage } from "@/utils/helpers";
import useComponentStore from "@/utils/useComponentStore";
import { useDropZone } from "@vueuse/core";
import { Ref } from "vue";

const store = useStore();
const componentStore = useComponentStore();

export function useCanvasDropZone(
	canvasContainer: Ref<HTMLElement>,
	block: Ref<Block | null>,
	findBlock: (id: string) => Block | null,
) {
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
	return { isOverDropZone };
}
