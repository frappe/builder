import type Block from "@/block";
import type BuilderCanvas from "@/components/BuilderCanvas.vue";
import type { IndicatorGeometry } from "@/utils/dropGeometry";
import { getVersionedDoc } from "@/data/snapshot";
import { confirm, getBlockCopy, getBlockInstance } from "@/utils/helpers";
import { toast } from "frappe-ui";
import { defineStore } from "pinia";
import { nextTick } from "vue";

const PREVIEW_TOAST_ID = "version-preview-readonly";

const useCanvasStore = defineStore("canvasStore", {
	state: () => ({
		activeCanvas: <InstanceType<typeof BuilderCanvas> | null>null,
		requiresConfirmationForCopyingEntirePage: <boolean>true,
		copyEntirePage: <boolean>false,
		layerDraggingOverBlock: <string | null>null,
		preventClick: false,
		isMarqueeActive: false,
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
		// On-canvas block reordering (pointer-based). Kept separate from dropTarget
		// (panel → canvas drops) so the two systems don't interfere. The overlay
		// DropIndicator reads this; nothing here mutates the canvas DOM, so the
		// layout stays stable during the drag.
		reorderTarget: {
			active: <boolean>false,
			// "slot": exact in-flow placeholder (same-container reorder, shifts siblings)
			// "line": no-reflow line between children (cross-container drop)
			mode: <"slot" | "line">"slot",
			// exact drop slot (screen px) — measured from the in-flow placeholder,
			// so it reflects the container's real flex/grid layout
			slotRect: <{ top: number; left: number; width: number; height: number } | null>null,
			// cross-container line indicator geometry (screen px)
			line: <IndicatorGeometry | null>null,
			containerRect: <{ top: number; left: number; width: number; height: number } | null>null,
			isComponentParent: <boolean>false,
			// spacing guide: the container's main-axis gap (px), positioned for a label
			spacing: <{ value: number; left: number; top: number } | null>null,
		},
		editableBlock: <Block | null>null,
		editingContentType: <"html" | "css" | "js">"html", // TODO: Remove js and css
		editingMode: <EditingMode>"page",
		settingPage: false,
		showEditorDialog: false,
		fragmentData: {
			block: <Block | null>null,
			fragmentType: <"component" | "blockTemplate" | null>null,
			saveAction: <Function | null>null,
			saveActionLabel: <string | null>null,
			fragmentName: <string | null>null,
			fragmentId: <string | null>null,
			showUsageCount: false,
		},
		versionPreviewBlock: <Block | null>null,
		previewSnapshotName: <string | null>null,
		draftRootBackup: <Block | null>null,
	}),
	actions: {
		// Preview a snapshot on the live page canvas itself so pan/zoom stay in place.
		// Setting versionPreviewBlock flips the canvas to read-only (PageBuilder.vue
		// watcher), which hibernates history — so swapping the root in/out never touches
		// the draft's content or undo stack. We just stash the draft root to restore it.
		async previewVersion(snapshotName: string) {
			const doc = await getVersionedDoc(snapshotName);
			const blocks = JSON.parse((doc?.draft_blocks || doc?.blocks || "[]") as string);
			if (!blocks[0] || !this.activeCanvas) return;
			const previewRoot = getBlockInstance(blocks[0]);
			if (!this.versionPreviewBlock) {
				this.draftRootBackup = this.activeCanvas.getRootBlock() ?? null;
			}
			this.activeCanvas.setRootBlock(previewRoot, false, false);
			this.versionPreviewBlock = previewRoot;
			this.previewSnapshotName = snapshotName;
			toast.info("Read-only preview · Use <b>Restore</b> to load this version.", {
				id: PREVIEW_TOAST_ID,
				duration: Infinity,
				dismissible: false,
				closeButton: false,
				position: "bottom-center",
			});
		},
		clearVersionPreview() {
			if (this.versionPreviewBlock && this.draftRootBackup && this.activeCanvas) {
				this.activeCanvas.setRootBlock(this.draftRootBackup, false, false);
			}
			this.draftRootBackup = null;
			this.versionPreviewBlock = null;
			this.previewSnapshotName = null;
			toast.dismiss(PREVIEW_TOAST_ID);
		},
		clearBlocks() {
			this.activeCanvas?.clearCanvas();
		},
		pushBlocks(blocks: BlockOptions[], resetHistory: boolean = true) {
			let parent = this.activeCanvas?.getRootBlock();
			let firstBlock = getBlockInstance(blocks[0]);

			if (this.editingMode === "page" && firstBlock.isRoot() && this.activeCanvas?.block) {
				this.activeCanvas.setRootBlock(firstBlock, false, resetHistory);
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
						.querySelector(`[data-block-layer-id="${block.blockId}"] .scroll-into-view-anchor`)
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
			this.editingContentType = "html";
			nextTick(() => {
				this.showEditorDialog = true;
			});
		},

		editOnCanvas(
			block: Block,
			fragmentType: "component" | "blockTemplate",
			saveAction: (block: Block) => void,
			saveActionLabel: string = "Save",
			fragmentName?: string,
			fragmentId?: string,
			showUsageCount?: boolean,
		) {
			const blockCopy = getBlockCopy(block, true);
			this.fragmentData = {
				block: blockCopy,
				fragmentType,
				saveAction,
				saveActionLabel,
				fragmentName: fragmentName || block.getBlockDescription(),
				fragmentId: fragmentId || block.blockId,
				showUsageCount: showUsageCount || false,
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
				fragmentType: null,
				saveAction: null,
				saveActionLabel: null,
				fragmentName: null,
				fragmentId: null,
				showUsageCount: false,
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

		clearReorderTarget() {
			this.reorderTarget = {
				active: false,
				mode: "slot",
				slotRect: null,
				line: null,
				containerRect: null,
				isComponentParent: false,
				spacing: null,
			};
		},
	},
});

export default useCanvasStore;
