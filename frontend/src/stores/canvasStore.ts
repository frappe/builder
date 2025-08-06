import type Block from "@/block";
import type BuilderCanvas from "@/components/BuilderCanvas.vue";
import { confirm, getBlockCopy, getBlockInstance } from "@/utils/helpers";
import { defineStore } from "pinia";
import { nextTick } from "vue";

const useCanvasStore = defineStore("canvasStore", {
	state: () => ({
		activeCanvas: <InstanceType<typeof BuilderCanvas> | null>null,
		requiresConfirmationForCopyingEntirePage: <boolean>true,
		copyEntirePage: <boolean>false,
		preventClick: false,
		guides: {
			showX: false,
			showY: false,
			x: 0,
			y: 0,
		},
		isDragging: false,
		isDropping: false,
		dropTarget: {
			x: <number | null>null,
			y: <number | null>null,
			placeholder: <HTMLElement | null>null,
			parentBlock: <Block | null>null,
			index: <number | null>null,
		},
		editableBlock: <Block | null>null,
		editingMode: <EditingMode>"page",
		settingPage: false,
		showHTMLDialog: false,
		fragmentData: {
			block: <Block | null>null,
			saveAction: <Function | null>null,
			saveActionLabel: <string | null>null,
			fragmentName: <string | null>null,
			fragmentId: <string | null>null,
		},
	}),
	actions: {
		clearBlocks() {
			this.activeCanvas?.clearCanvas();
		},
		pushBlocks(blocks: BlockOptions[]) {
			let parent = this.activeCanvas?.getRootBlock();
			let firstBlock = getBlockInstance(blocks[0]);

			if (this.editingMode === "page" && firstBlock.isRoot() && this.activeCanvas?.block) {
				this.activeCanvas.setRootBlock(firstBlock);
			} else {
				for (let block of blocks) {
					parent?.addChild(block);
				}
			}
		},

		getRootBlock() {
			return this.activeCanvas?.getRootBlock();
		},

		getPageBlocks() {
			return [this.activeCanvas?.getRootBlock()];
		},
		selectBlock(
			block: Block,
			e: MouseEvent | null,
			scrollLayerIntoView: boolean | ScrollLogicalPosition = true,
			scrollBlockIntoView = false,
		) {
			if (this.settingPage) {
				return;
			}

			if (e && e.shiftKey) {
				this.activeCanvas?.selectBlockRange(block);
			} else if (e && e.metaKey) {
				this.activeCanvas?.toggleBlockSelection(block);
			} else {
				this.activeCanvas?.selectBlock(block);
			}

			if (scrollLayerIntoView) {
				const align = scrollLayerIntoView === true ? "center" : scrollLayerIntoView;
				nextTick(() => {
					document
						.querySelector(`[data-block-layer-id="${block.blockId}"]`)
						?.scrollIntoView({ behavior: "instant", block: align, inline: "center" });
				});
			}

			this.editableBlock = null;

			if (scrollBlockIntoView) {
				this.activeCanvas?.scrollBlockIntoView(block);
			}
		},

		editHTML(block: Block) {
			this.editableBlock = block;
			nextTick(() => {
				this.showHTMLDialog = true;
			});
		},

		editOnCanvas(
			block: Block,
			saveAction: (block: Block) => void,
			saveActionLabel: string = "Save",
			fragmentName?: string,
			fragmentId?: string,
		) {
			const blockCopy = getBlockCopy(block, true);
			this.fragmentData = {
				block: blockCopy,
				saveAction,
				saveActionLabel,
				fragmentName: fragmentName || block.getBlockDescription(),
				fragmentId: fragmentId || block.blockId,
			};
			this.editingMode = "fragment";
		},

		async exitFragmentMode(e?: Event) {
			if (this.editingMode === "page") {
				return;
			}

			e?.preventDefault();

			if (this.activeCanvas?.isDirty) {
				const exit = await confirm("Are you sure you want to exit without saving?");
				if (!exit) {
					return;
				}
			}

			this.activeCanvas?.clearSelection();
			this.editingMode = "page";

			// reset fragmentData
			this.fragmentData = {
				block: null,
				saveAction: null,
				saveActionLabel: null,
				fragmentName: null,
				fragmentId: null,
			};
		},

		// Drag and drop handling
		handleDragStart(ev: DragEvent) {
			if (ev.target && ev.dataTransfer) {
				this.isDragging = true;
				const ghostScale = this.activeCanvas?.canvasProps.scale;

				// Clone the entire draggable element
				const dragElement = ev.target as HTMLElement;
				if (!dragElement) return;
				const ghostDiv = document.createElement("div");
				const ghostElement = dragElement.cloneNode(true) as HTMLElement;
				ghostDiv.appendChild(ghostElement);
				ghostDiv.id = "ghost";
				ghostDiv.style.position = "fixed";
				ghostDiv.style.transform = `scale(${ghostScale || 1})`;
				ghostDiv.style.pointerEvents = "none";
				ghostDiv.style.zIndex = "99999";
				// Append the ghostDiv to the DOM
				document.body.appendChild(ghostDiv);

				// Wait for the next frame to ensure the ghostDiv is rendered
				requestAnimationFrame(() => {
					ev.dataTransfer?.setDragImage(ghostDiv, 0, 0);
					// Clean up the ghostDiv after a short delay
					setTimeout(() => {
						document.body.removeChild(ghostDiv);
					}, 0);
				});
				this.insertDropPlaceholder();
			}
		},

		handleDragEnd() {
			// check flag to avoid race condition with async onDrop
			if (!this.isDropping) {
				this.resetDropTarget();
			}
		},

		resetDropTarget() {
			this.removeDropPlaceholder();
			this.dropTarget = {
				x: null,
				y: null,
				placeholder: null,
				parentBlock: null,
				index: null,
			};
			this.isDragging = false;
			this.isDropping = false;
		},

		insertDropPlaceholder() {
			// append placeholder component to the dom directly
			// to avoid re-rendering the whole canvas
			if (this.dropTarget.placeholder) return;

			let element = document.createElement("div");
			element.id = "placeholder";

			const root = document.querySelector(".__builder_component__[data-block-id='root']");
			if (root) {
				this.dropTarget.placeholder = root.appendChild(element);
			}
			return this.dropTarget.placeholder;
		},

		removeDropPlaceholder() {
			const placeholder = document.getElementById("placeholder");
			if (placeholder) {
				placeholder.remove();
			}
		},
	},
});

export default useCanvasStore;
