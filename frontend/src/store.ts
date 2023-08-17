import { UseRefHistoryReturn, useDebouncedRefHistory } from "@vueuse/core";
import { FileUploadHandler, toast } from "frappe-ui";
import { defineStore, storeToRefs } from "pinia";
import { reactive } from "vue";
import webComponent from "./data/webComponent";
import { webPages } from "./data/webPage";
import { WebPageBeta } from "./types/WebsiteBuilder/WebPageBeta";
import Block from "./utils/block";
import getBlockTemplate from "./utils/blockTemplate";
import { stripExtension } from "./utils/helpers";

const useStore = defineStore("store", {
	state: () => ({
		builderState: {
			editableBlock: <Block | null>null,
			blocks: <Block[]>[reactive(new Block(getBlockTemplate("body")))],
		},
		editingComponent: <string | null>null,
		editingMode: <EditingMode>"page",
		activeBreakpoint: "desktop",
		selectedPage: <string | null>null,
		pageData: <{ [key: string]: [] }>{},
		mode: <BuilderMode>"select",
		selectedBlocks: <Block[]>[],
		history: {} as UseRefHistoryReturn<{}, {}>,
		usedComponents: {},
		hoveredBlock: <string | null>null,
		hoveredBreakpoint: <string | null>null,
		routeVariables: <{ [key: string]: string }>{},
		builderLayout: {
			rightPanelWidth: 270,
			leftPanelWidth: 280,
		},
		flow: [
			{
				name: "Row",
				styleKey: "flexDirection",
				styleValue: "row",
				icon: "columns",
			},
			{
				name: "Column",
				styleKey: "flexDirection",
				styleValue: "column",
				icon: "credit-card",
			},
		],
		alignments: [
			{
				name: "Left",
				styleKey: "justifyContent",
				styleValue: "flex-start",
				icon: "align-left",
			},
			{
				name: "Center",
				styleKey: "justifyContent",
				styleValue: "center",
				icon: "align-center",
			},
			{
				name: "Right",
				styleKey: "justifyContent",
				styleValue: "flex-end",
				icon: "align-right",
			},
			{
				name: "Justify",
				styleKey: "justifyContent",
				styleValue: "space-between",
				icon: "align-justify",
			},
		],
		verticalAlignments: [
			{
				name: "Top",
				styleKey: "alignItems",
				styleValue: "flex-start",
				icon: "arrow-up",
			},
			{
				name: "Middle",
				styleKey: "alignItems",
				styleValue: "center",
				icon: "minus",
			},
			{
				name: "Bottom",
				styleKey: "alignItems",
				styleValue: "flex-end",
				icon: "arrow-down",
			},
		],
		pageName: "Home",
		route: "/",
		pastelCssColors: [
			"#FFFFFF",
			"#F5FFFA",
			"#F8F8FF",
			"#F0F8FF",
			"#F5F5DC",
			"#FFE4C4",
			"#FFEBCD",
			"#FFDEAD",
			"#FFC1C1",
			"#FFB6C1",
			"#FFA07A",
			"#FF8C00",
			"#FF7F50",
			"#FF69B4",
			"#FF6347",
			"#FDB813",
			"#FDAB9F",
			"#FDA50F",
			"#F49AC2",
			"#FFB347",
			"#FFD700",
			"#ADFF2F",
			"#87CEFA",
			"#00BFFF",
			"#ADD8E6",
			"#B0E0E6",
			"#5F9EA0",
			"#FDD5B1",
			"#FCCDE3",
			"#FCC2D9",
			"#FCB4D5",
			"#FBB5A3",
			"#FBB917",
			"#FBB972",
			"#FBB9AC",
			"#FBCEB1",
			"linear-gradient(120deg, #f093fb 0%, #f5576c 100%)",
			"linear-gradient(to top, #a18cd1 0%, #fbc2eb 100%)",
			"linear-gradient(to top, #a8edea 0%, #fed6e3 100%)",
			"linear-gradient(to top, #96fbc4 0%, #f9f586 100%)",
			"linear-gradient(to top, #9795f0 0%, #fbc8d4 100%)",
			"linear-gradient(-60deg, #16a085 0%, #f4d03f 100%)",
			"linear-gradient( 135deg, #81FFEF 10%, #F067B4 100%)",
			"black",
			"transparent",
		],
		guides: {
			showX: false,
			showY: false,
			x: 0,
			y: 0,
		},
		textColors: [
			"#000000",
			"#424242",
			"#636363",
			"#808080",
			"#9C9C94",
			"#C0C0C0",
			"#CEC6CE",
			"#EFEFEF",
			"#F7F7F7",
			"#FFFFFF",
		],
		deviceBreakpoints: [
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
				width: 640,
				visible: false,
			},
		],
		sidebarActiveTab: <LeftSidebarTabOption>"Components",
		showPanels: <boolean>true,
		blockEditorCanvas: {
			scale: 0.5,
			translateX: 0,
			translateY: 0,
			startX: 0,
			startY: 0,
			background: "",
			scaling: false,
			panning: false,
			settingCanvas: true,
			overlayElement: <HTMLElement | null>null,
		},
		componentEditorCanvas: {
			scale: 0.5,
			translateX: 0,
			translateY: 0,
			startX: 0,
			startY: 0,
			background: "",
			scaling: false,
			panning: false,
			settingCanvas: false,
			overlayElement: <HTMLElement | null>null,
		},
		copiedStyle: <StyleCopy | null>null,
		components: <BlockComponent[]>[],
	}),
	actions: {
		clearBlocks() {
			this.builderState.blocks = [];
			this.builderState.blocks.push(this.getRootBlock());
		},
		pushBlocks(blocks: BlockOptions[]) {
			let parent = this.builderState.blocks[0];
			if (this.editingComponent) {
				parent = this.getComponentBlock(this.editingComponent);
			}
			let firstBlock = reactive(new Block(blocks[0]));
			if (firstBlock.isRoot() && !this.editingComponent) {
				this.builderState.blocks = [firstBlock];
			} else {
				for (let block of blocks) {
					parent.children.push(this.getBlockInstance(block));
				}
			}
		},
		getFirstBlock() {
			return this.editingComponent
				? this.getComponentBlock(this.editingComponent)
				: this.builderState.blocks[0];
		},
		getBlockCopy(block: BlockOptions | Block, retainId = false): Block {
			let b = JSON.parse(JSON.stringify(block));
			if (!retainId) {
				const deleteBlockId = (block: BlockOptions) => {
					delete block.blockId;
					for (let child of block.children || []) {
						deleteBlockId(child);
					}
				};
				deleteBlockId(b);
			}
			return reactive(new Block(b));
		},
		getRootBlock() {
			return reactive(new Block(getBlockTemplate("body")));
		},
		getPageData() {
			return this.builderState.blocks;
		},
		setPage(page: WebPageBeta) {
			if (!page) {
				return;
			}
			// clear blocks
			this.editPage();
			this.clearBlocks();
			this.pushBlocks(page.blocks);
			this.pageName = page.page_name as string;
			this.route = page.route || "/" + this.pageName.toLowerCase().replace(/ /g, "-");
			this.selectedPage = page.name;
			this.setPageData();
			this.setupHistory();
			// localStorage.setItem("selectedPage", page.name);
		},
		getImageBlock(imageSrc: string, imageAlt: string = "") {
			imageAlt = stripExtension(imageAlt);
			const imageBlock = getBlockTemplate("image");
			if (!imageBlock.attributes) {
				imageBlock.attributes = {};
			}
			imageBlock.attributes.src = imageSrc;
			if (imageAlt) {
				imageBlock.attributes.alt = imageAlt;
			}

			return imageBlock;
		},
		findBlock(blockId: string, blocks?: Array<Block>): Block | null {
			if (!blocks) {
				blocks = this.builderState.blocks;
			}
			for (const block of blocks) {
				if (block.blockId === blockId) {
					return block;
				}
				if (block.children) {
					const found = this.findBlock(blockId, block.children);
					if (found) {
						return found;
					}
				}
			}
			return null;
		},
		findParentBlock(blockId: string, blocks?: Array<Block>): Block | null {
			if (!blocks) {
				blocks = this.builderState.blocks;
			}
			for (const block of blocks) {
				if (block.children) {
					for (const child of block.children) {
						if (child.blockId === blockId) {
							return block;
						}
					}
					const found = this.findParentBlock(blockId, block.children);
					if (found) {
						return found;
					}
				}
			}
			return null;
		},
		selectBlock(block: Block, e: MouseEvent | null, scrollIntoView = true) {
			if (e && e.shiftKey) {
				block.toggleSelectBlock();
			} else {
				block.selectBlock();
			}
			if (scrollIntoView) {
				// TODO: move to layers?
				document
					.querySelector(`[data-block-layer-id="${block.blockId}"]`)
					?.scrollIntoView({ behavior: "instant", block: "center" });
			}
			this.builderState.editableBlock = null;
		},
		getBlockInstance(options: BlockOptions) {
			return reactive(new Block(options));
		},
		editComponent(block: Block) {
			if (block.isComponent()) {
				this.editingComponent = block?.extendedFromComponent as string;
			}
			this.clearSelection();
			this.editingMode = "component";
		},
		isComponentUsed(componentName: string) {
			// TODO: Refactor or reduce complexity
			const checkComponent = (block: Block) => {
				if (block.extendedFromComponent === componentName) {
					return true;
				}
				if (block.children) {
					for (const child of block.children) {
						if (checkComponent(child)) {
							return true;
						}
					}
				}
				return false;
			};
			for (const block of this.builderState.blocks) {
				if (checkComponent(block)) {
					return true;
				}
			}
			return false;
		},
		editPage(saveComponent = false) {
			this.clearSelection();
			this.editingMode = "page";
			this.builderState.editableBlock = null;

			if (this.editingComponent) {
				if (saveComponent) {
					webComponent.setValue
						.submit({
							name: this.editingComponent,
							block: this.getComponentBlock(this.editingComponent),
						})
						.then(() => {
							toast({
								text: "Component saved!",
								position: "bottom-center",
							});
						});
				} else {
					// webComponent.fet;
				}
			}
			this.editingComponent = null;
		},
		getComponentBlock(componentName: string) {
			return webComponent.getRow(componentName).block as Block;
		},
		getComponentName(componentId: string) {
			let componentObj = webComponent.getRow(componentId);
			if (!componentObj) {
				return componentId;
			}
			return componentObj.component_name as Block;
		},
		setupHistory() {
			const { builderState } = storeToRefs(this);
			this.history = useDebouncedRefHistory(builderState, {
				capacity: 50,
				deep: true,
				clone: (obj) => {
					let newObj = Object.assign({}, obj);
					newObj.blocks = obj.blocks.map((val: Block) => this.getBlockCopy(val, true));
					return newObj;
				},
				debounce: 200,
			}) as unknown as typeof this.history;
		},
		uploadFile(file: File) {
			const uploader = new FileUploadHandler();
			return uploader
				.upload(file, {
					private: false,
					optimize: true,
				})
				.then((fileDoc: { file_url: string; file_name: string }) => {
					const fileURL = encodeURI(window.location.origin + fileDoc.file_url);
					return {
						fileURL,
						fileName: fileDoc.file_name,
					};
				});
		},
		clearSelection() {
			this.selectedBlocks = [];
		},
		getActivePage() {
			return webPages.getRow(this.selectedPage as string) as WebPageBeta;
		},
		savePage(open_preview = false) {
			return webPages.setValue
				.submit({
					name: this.selectedPage,
					blocks: JSON.stringify(this.getPageData()),
				})
				.then((doc: WebPageBeta) => {
					if (open_preview) {
						window.open(`/${doc.route}`, "preview-page");
					}
				});
		},
		setPageData() {
			const page = this.getActivePage();
			if (!page.page_data_script) {
				return;
			}
			webPages.runDocMethod
				.submit({
					method: "get_page_data",
					name: page.name,
					...this.routeVariables,
				})
				.then((data: { message: { [key: string]: [] } }) => {
					this.pageData = data.message;
				})
				.catch(() => {
					toast({
						text: "There was error in fetching page data",
						position: "top-right",
						icon: "disabled",
						iconClasses: "text-red-500",
					});
				});
		},
	},
});

export default useStore;
