import { UseRefHistoryReturn } from "@vueuse/core";
import { FileUploadHandler } from "frappe-ui";
import { defineStore } from "pinia";
import { nextTick } from "vue";
import { toast } from "vue-sonner";
import BuilderCanvas from "./components/BuilderCanvas.vue";
import webComponent from "./data/webComponent";
import { webPages } from "./data/webPage";
import { BuilderComponent } from "./types/Builder/BuilderComponent";
import { BuilderPage } from "./types/Builder/BuilderPage";
import Block from "./utils/block";
import getBlockTemplate from "./utils/blockTemplate";
import { getBlockInstance, stripExtension } from "./utils/helpers";

const useStore = defineStore("store", {
	state: () => ({
		editableBlock: <Block | null>null,
		settingPage: false,
		editingComponent: <string | null>null,
		editingMode: <EditingMode>"page",
		activeBreakpoint: "desktop",
		selectedPage: <string | null>null,
		pageData: <{ [key: string]: [] }>{},
		mode: <BuilderMode>"select", // check setEvents in BuilderCanvas for usage
		selectedBlocks: <Block[]>[],
		activeCanvas: <InstanceType<typeof BuilderCanvas> | null>null,
		history: {
			pause: () => {},
			resume: () => {},
		} as UseRefHistoryReturn<{}, {}>,
		hoveredBlock: <string | null>null,
		hoveredBreakpoint: <string | null>null,
		routeVariables: <{ [key: string]: string }>{},
		autoSave: true,
		pageBlocks: <Block[]>[],
		propertyFilter: <string | null>null,
		builderLayout: {
			rightPanelWidth: 275,
			leftPanelWidth: 280,
			scriptEditorHeight: 300,
		},
		pageName: "Home",
		route: "/",
		guides: {
			showX: false,
			showY: false,
			x: 0,
			y: 0,
		},
		leftPanelActiveTab: <LeftSidebarTabOption>"Layers",
		rightPanelActiveTab: <RightSidebarTabOption>"Properties",
		showRightPanel: <boolean>true,
		showLeftPanel: <boolean>true,
		copiedStyle: <StyleCopy | null>null,
		components: <BlockComponent[]>[],
	}),
	actions: {
		clearBlocks() {
			this.activeCanvas?.clearCanvas();
		},
		pushBlocks(blocks: BlockOptions[]) {
			let parent = this.activeCanvas?.getFirstBlock();
			let firstBlock = getBlockInstance(blocks[0]);
			if (firstBlock.isRoot() && !this.editingComponent && this.activeCanvas?.block) {
				this.activeCanvas.setRootBlock(firstBlock);
			} else {
				for (let block of blocks) {
					parent?.children.push(getBlockInstance(block));
				}
			}
		},
		getFirstBlock() {
			return this.activeCanvas?.getFirstBlock();
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
			return getBlockInstance(b);
		},
		getRootBlock() {
			return getBlockInstance(getBlockTemplate("body"));
		},
		getPageData() {
			return [this.activeCanvas?.getFirstBlock()];
		},
		async setPage(page: BuilderPage, resetCanvas = true) {
			this.settingPage = true;
			if (!page) {
				return;
			}
			const blocks = JSON.parse(page.draft_blocks || page.blocks || "[]");
			this.editPage();
			if (!Array.isArray(blocks)) {
				this.pushBlocks([blocks]);
			}
			this.pageBlocks = [getBlockInstance(blocks[0])];
			this.pageName = page.page_name as string;
			this.route = page.route || "/" + this.pageName.toLowerCase().replace(/ /g, "-");
			this.selectedPage = page.name;
			const variables = localStorage.getItem(`${page.name}:routeVariables`) || "{}";
			this.routeVariables = JSON.parse(variables);
			await this.setPageData();
			this.activeCanvas?.setRootBlock(this.pageBlocks[0], resetCanvas);
			nextTick(() => {
				this.settingPage = false;
			});
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
				blocks = [this.activeCanvas?.getFirstBlock() as Block];
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
				const firstBlock = this.activeCanvas?.getFirstBlock() as Block;
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
					const found = this.findParentBlock(blockId, block.children);
					if (found) {
						return found;
					}
				}
			}
			return null;
		},
		selectBlock(block: Block, e: MouseEvent | null, scrollIntoView = true) {
			this.activeCanvas?.history?.pause();
			if (this.settingPage) {
				return;
			}
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
			this.activeCanvas?.history?.resume();
			this.editableBlock = null;
		},
		editComponent(block: Block) {
			if (block.isExtendedFromComponent()) {
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
			for (const block of this.activeCanvas?.getFirstBlock()?.children || []) {
				if (checkComponent(block)) {
					return true;
				}
			}
			return false;
		},
		editPage(saveComponent = false) {
			this.clearSelection();
			this.editingMode = "page";
			this.editableBlock = null;

			if (this.editingComponent) {
				if (saveComponent) {
					webComponent.setValue
						.submit({
							name: this.editingComponent,
							block: this.activeCanvas?.getFirstBlock(),
						})
						.then(() => {
							toast.success("Component saved!");
						});
				} else {
					// webComponent.fet;
				}
			}
			this.editingComponent = null;
		},
		getComponentBlock(componentName: string) {
			return (this.getComponent(componentName)?.block as Block) || this.getFallbackBlock();
		},
		getComponent(componentName: string) {
			return webComponent.getRow(componentName) as BuilderComponent;
		},
		createComponent(obj: BuilderComponent, updateExisting = false) {
			const component = this.getComponent(obj.name);
			if (component) {
				const existingComponent = JSON.stringify(component.block);
				const newComponent = JSON.stringify(obj.block);
				if (updateExisting && existingComponent !== newComponent) {
					return webComponent.setValue.submit({
						name: obj.name,
						block: obj.block,
					});
				} else {
					return;
				}
			}
			return webComponent.insert.submit(obj).catch(() => {
				console.log(`There was an error while creating ${obj.component_name}`);
			});
		},
		getFallbackBlock() {
			return getBlockInstance(getBlockTemplate("fallback-component"));
		},
		getComponentName(componentId: string) {
			let componentObj = webComponent.getRow(componentId);
			if (!componentObj) {
				return componentId;
			}
			return componentObj.component_name as Block;
		},
		uploadFile: async (file: File) => {
			const uploader = new FileUploadHandler();
			let fileDoc = {
				file_url: "",
				file_name: "",
			};
			const upload = uploader.upload(file, {
				private: false,
				folder: "Home/Builder Uploads",
				optimize: true,
			});
			await new Promise((resolve) => {
				toast.promise(upload, {
					loading: "Uploading...",
					success: (data: { file_name: string; file_url: string }) => {
						fileDoc.file_name = data.file_name;
						fileDoc.file_url = data.file_url;
						resolve(fileDoc);
						return "Uploaded";
					},
					error: () => "Failed to upload",
					duration: 500,
				});
			});

			return {
				fileURL: encodeURI(window.location.origin + fileDoc.file_url),
				fileName: fileDoc.file_name,
			};
		},
		clearSelection() {
			this.selectedBlocks = [];
		},
		isSelected(blockId: string) {
			return this.selectedBlocks.some((block) => block.blockId === blockId);
		},
		getActivePage() {
			return webPages.getRow(this.selectedPage as string) as BuilderPage;
		},
		async publishPage() {
			return webPages.runDocMethod
				.submit({
					name: this.selectedPage as string,
					method: "publish",
					...this.routeVariables,
				})
				.then(() => {
					this.openPageInBrowser();
				});
		},
		openPageInBrowser() {
			const page = this.getActivePage();
			let route = page.route;
			if (page.dynamic_route && this.pageData) {
				const routeVariables = (route?.match(/<\w+>/g) || []).map((match: string) => match.slice(1, -1));
				routeVariables.forEach((variable: string) => {
					if (this.routeVariables[variable]) {
						route = route?.replace(`<${variable}>`, this.routeVariables[variable]);
					}
				});
			}
			window.open(`/${route}`, "builder-preview");
		},
		savePage() {
			this.pageBlocks = this.getPageData() as Block[];
			const pageData = JSON.stringify(this.pageBlocks);

			const args = {
				name: this.selectedPage,
				draft_blocks: pageData,
			};
			webPages.setValue.submit(args);
		},
		setPageData() {
			const page = this.getActivePage();
			if (!page || !page.page_data_script) {
				this.pageData = {};
				return;
			}
			return webPages.runDocMethod
				.submit({
					method: "get_page_data",
					name: page.name,
					...this.routeVariables,
				})
				.then((data: { message: { [key: string]: [] } }) => {
					this.pageData = data.message;
				})
				.catch((e: { exc: string }) => {
					const error_message = e.exc.split("\n").slice(-2)[0];
					toast.error("There was an error while fetching page data", {
						description: error_message,
					});
				});
		},
		setRouteVariable(variable: string, value: string) {
			this.routeVariables[variable] = value;
			localStorage.setItem(`${this.selectedPage}:routeVariables`, JSON.stringify(this.routeVariables));
			this.setPageData();
		},
		openInDesk(page: BuilderPage) {
			window.open(`/app/builder-page/${page.page_name}`, "_blank");
		},
		openBuilderSettings() {
			window.open("/app/builder-settings", "_blank");
		},
	},
});

export default useStore;
