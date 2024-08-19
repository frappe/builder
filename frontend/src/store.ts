import { posthog } from "@/telemetry";
import { UseRefHistoryReturn } from "@vueuse/core";
import { FileUploadHandler, createDocumentResource } from "frappe-ui";
import { defineStore } from "pinia";
import { nextTick } from "vue";
import { toast } from "vue-sonner";
import BlockLayers from "./components/BlockLayers.vue";
import BuilderCanvas from "./components/BuilderCanvas.vue";
import builderBlockTemplate from "./data/builderBlockTemplate";
import { builderSettings } from "./data/builderSettings";
import webComponent from "./data/webComponent";
import { webPages } from "./data/webPage";
import { BlockTemplate } from "./types/Builder/BlockTemplate";
import { BuilderComponent } from "./types/Builder/BuilderComponent";
import { BuilderPage } from "./types/Builder/BuilderPage";
import Block from "./utils/block";
import getBlockTemplate from "./utils/blockTemplate";
import {
	confirm,
	getBlockCopy,
	getBlockInstance,
	getBlockObject,
	getBlockString,
	getCopyWithoutParent,
} from "./utils/helpers";
import RealTimeHandler from "./utils/realtimeHandler";

const useStore = defineStore("store", {
	state: () => ({
		editableBlock: <Block | null>null,
		settingPage: false,
		editingMode: <EditingMode>"page",
		activeBreakpoint: "desktop",
		selectedPage: <string | null>null,
		pageData: <{ [key: string]: [] }>{},
		mode: <BuilderMode>"select", // check setEvents in BuilderCanvas for usage
		lastMode: <BuilderMode>"select",
		activeCanvas: <InstanceType<typeof BuilderCanvas> | null>null,
		activeLayers: <InstanceType<typeof BlockLayers> | null>null,
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
		components: <BlockComponent[]>[],
		showHTMLDialog: false,
		activePage: <BuilderPage | null>null,
		savingPage: false,
		realtime: new RealTimeHandler(),
		viewers: <UserInfo[]>[],
		componentMap: <Map<string, Block>>new Map(),
		fragmentData: {
			block: <Block | null>null,
			saveAction: <Function | null>null,
			saveActionLabel: <string | null>null,
			fragmentName: <string | null>null,
		},
	}),
	actions: {
		clearBlocks() {
			this.activeCanvas?.clearCanvas();
		},
		pushBlocks(blocks: BlockOptions[]) {
			let parent = this.activeCanvas?.getFirstBlock();
			let firstBlock = getBlockInstance(blocks[0]);
			if (this.editingMode === "page" && firstBlock.isRoot() && this.activeCanvas?.block) {
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
			return getBlockCopy(block, retainId);
		},
		getRootBlock() {
			return getBlockInstance(getBlockTemplate("body"));
		},
		getPageBlocks() {
			return [this.activeCanvas?.getFirstBlock()];
		},
		async setPage(pageName: string, resetCanvas = true) {
			this.settingPage = true;
			if (!pageName) {
				return;
			}

			const page = await this.fetchActivePage(pageName);
			if (!page) {
				toast.error("Page not found");
				return;
			}
			this.activePage = page;

			const blocks = JSON.parse(page.draft_blocks || page.blocks || "[]");
			this.editPage(!resetCanvas);
			if (!Array.isArray(blocks)) {
				this.pushBlocks([blocks]);
			}
			if (blocks.length === 0) {
				this.pageBlocks = [getBlockInstance(getBlockTemplate("body"))];
			} else {
				this.pageBlocks = [getBlockInstance(blocks[0])];
			}
			this.pageBlocks = [getBlockInstance(blocks[0] || getBlockTemplate("body"))];
			this.pageName = page.page_name as string;
			this.route = page.route || "/" + this.pageName.toLowerCase().replace(/ /g, "-");
			this.selectedPage = page.name;
			const variables = localStorage.getItem(`${page.name}:routeVariables`) || "{}";
			this.routeVariables = JSON.parse(variables);
			await this.setPageData(this.activePage);
			this.activeCanvas?.setRootBlock(this.pageBlocks[0], resetCanvas);
			nextTick(() => {
				this.settingPage = false;
			});
		},
		async setActivePage(pageName: string) {
			this.selectedPage = pageName;
			const page = await this.fetchActivePage(pageName);
			if (!page) {
				return;
			}
			this.activePage = page;
		},
		async fetchActivePage(pageName: string) {
			const webPageResource = await createDocumentResource({
				doctype: "Builder Page",
				name: pageName,
				auto: true,
			});
			try {
				await webPageResource.get.promise;
			} catch (e) {
				return null;
			}

			const page = webPageResource.doc as BuilderPage;
			return page;
		},
		getImageBlock(imageSrc: string, imageAlt: string = "") {
			const imageBlock = getBlockTemplate("image");
			if (!imageBlock.attributes) {
				imageBlock.attributes = {};
			}
			imageBlock.attributes.src = imageSrc;

			return imageBlock;
		},
		getVideoBlock(videoSrc: string) {
			const videoBlock = getBlockTemplate("video");
			if (!videoBlock.attributes) {
				videoBlock.attributes = {};
			}
			videoBlock.attributes.src = videoSrc;
			return videoBlock;
		},
		selectBlock(block: Block, e: MouseEvent | null, scrollLayerIntoView = true, scrollBlockIntoView = false) {
			this.activeCanvas?.history?.pause();
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
				// TODO: move to layers?
				nextTick(() => {
					document
						.querySelector(`[data-block-layer-id="${block.blockId}"]`)
						?.scrollIntoView({ behavior: "instant", block: "center", inline: "center" });
				});
			}

			this.activeCanvas?.history?.resume();
			this.editableBlock = null;
			if (scrollBlockIntoView) {
				this.activeCanvas?.scrollBlockIntoView(block);
			}
		},
		editComponent(block?: Block | null, componentName?: string) {
			if (!block?.isExtendedFromComponent() && !componentName) {
				return;
			}
			componentName = componentName || (block?.extendedFromComponent as string);
			const component = this.getComponent(componentName);
			const componentBlock = this.getComponentBlock(componentName);
			this.editOnCanvas(
				componentBlock,
				(block: Block) => {
					webComponent.setValue
						.submit({
							name: componentName,
							block: getBlockObject(block),
						})
						.then((data: BuilderComponent) => {
							this.componentMap.set(data.name, getBlockInstance(data.block));
							toast.success("Component saved!");
						});
				},
				"Save Component",
				component.component_name,
			);
		},
		editBlockTemplate(blockTemplateName: string) {
			const blockTemplate = this.getBlockTemplate(blockTemplateName);
			const blockTemplateBlock = this.getBlockTemplateBlock(blockTemplateName);
			this.editOnCanvas(
				blockTemplateBlock,
				(block: Block) => {
					this.saveBlockTemplate(block, blockTemplateName);
				},
				"Save Template",
				blockTemplate.template_name,
			);
		},
		getBlockTemplateBlock(blockTemplateName: string) {
			return getBlockInstance(this.getBlockTemplate(blockTemplateName).block);
		},
		getBlockTemplate(blockTemplateName: string) {
			return builderBlockTemplate.getRow(blockTemplateName) as BlockTemplate;
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
		editPage(retainSelection = false) {
			if (!retainSelection) {
				this.activeCanvas?.clearSelection();
			}
			this.editingMode = "page";
		},
		getComponentBlock(componentName: string) {
			if (!this.componentMap.has(componentName)) {
				this.componentMap.set(
					componentName,
					getBlockInstance(this.getComponent(componentName)?.block || getBlockTemplate("fallback-component")),
				);
			}
			return this.componentMap.get(componentName) as Block;
		},
		getComponent(componentName: string) {
			return webComponent.getRow(componentName) as BuilderComponent;
		},
		createComponent(obj: BuilderComponent, updateExisting = false) {
			const component = this.getComponent(obj.name);
			if (component) {
				const existingComponent = component.block;
				const newComponent = obj.block;
				if (updateExisting && existingComponent !== newComponent) {
					return webComponent.setValue.submit({
						name: obj.name,
						block: obj.block,
					});
				} else {
					return;
				}
			}
			return webComponent.insert
				.submit(obj)
				.then(() => {
					this.componentMap.set(obj.name, getBlockInstance(obj.block));
				})
				.catch(() => {
					console.log(`There was an error while creating ${obj.component_name}`);
				});
		},
		getComponentName(componentId: string) {
			let componentObj = webComponent.getRow(componentId);
			if (!componentObj) {
				return componentId;
			}
			return componentObj.component_name;
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
				upload_endpoint: "/api/method/builder.builder.doctype.builder_page.builder_page.upload_builder_asset",
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
				fileURL: fileDoc.file_url,
				fileName: fileDoc.file_name,
			};
		},
		deletePage: async (page: BuilderPage) => {
			const confirmed = await confirm(
				`Are you sure you want to delete page: ${page.page_title || page.page_name}?`,
			);
			if (confirmed) {
				await webPages.delete.submit(page.name);
			}
			toast.success("Page deleted successfully!");
		},
		async publishPage() {
			await this.waitTillPageIsSaved();
			return webPages.runDocMethod
				.submit({
					name: this.selectedPage as string,
					method: "publish",
					...this.routeVariables,
				})
				.then(async () => {
					posthog.capture("builder_page_published", {
						page: this.selectedPage,
					});
					this.activePage = await this.fetchActivePage(this.selectedPage as string);
					this.openPageInBrowser(this.activePage as BuilderPage);
				});
		},
		unpublishPage() {
			return webPages.setValue
				.submit({
					name: this.selectedPage,
					published: false,
				})
				.then(() => {
					toast.success("Page unpublished");
					this.setPage(this.selectedPage as string);
					builderSettings.reload();
				});
		},
		updateActivePage(key: keyof BuilderPage, value: any) {
			if (!this.activePage) {
				return;
			}
			return webPages.setValue
				.submit({
					name: this.activePage.name as string,
					[key]: value,
				})
				.then(() => {
					if (this.activePage) {
						this.activePage[key] = value;
					}
				});
		},
		openPageInBrowser(page: BuilderPage) {
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
			this.pageBlocks = this.getPageBlocks() as Block[];
			const pageData = JSON.stringify(this.pageBlocks.map((block) => getCopyWithoutParent(block)));

			const args = {
				name: this.selectedPage,
				draft_blocks: pageData,
			};
			return webPages.setValue
				.submit(args)
				.then((page: BuilderPage) => {
					this.activePage = page;
				})
				.finally(() => {
					this.savingPage = false;
					this.activeCanvas?.toggleDirty(false);
				});
		},
		setPageData(page?: BuilderPage) {
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
				.catch((e: { exc: string | null }) => {
					const error_message = e.exc?.split("\n").slice(-2)[0];
					toast.error("There was an error while fetching page data", {
						description: error_message,
					});
				});
		},
		setRouteVariable(variable: string, value: string) {
			this.routeVariables[variable] = value;
			localStorage.setItem(`${this.selectedPage}:routeVariables`, JSON.stringify(this.routeVariables));
			this.setPageData(this.activePage as BuilderPage);
		},
		openInDesk(page: BuilderPage) {
			window.open(`/app/builder-page/${page.page_name}`, "_blank");
		},
		openBuilderSettings() {
			window.open("/app/builder-settings", "_blank");
		},
		editHTML(block: Block) {
			this.editableBlock = block;
			nextTick(() => {
				this.showHTMLDialog = true;
			});
		},
		isHomePage(page: BuilderPage | null = null) {
			return builderSettings.doc.home_page === (page || this.activePage)?.route;
		},
		async waitTillPageIsSaved() {
			// small delay so that all the save requests are triggered
			await new Promise((resolve) => setTimeout(resolve, 100));
			return new Promise((resolve) => {
				const interval = setInterval(() => {
					if (!this.savingPage) {
						clearInterval(interval);
						resolve(null);
					}
				}, 100);
			});
		},
		async saveBlockTemplate(
			block: Block,
			templateName: string,
			category: BlockTemplate["category"] = "Basic",
			previewImage: string = "",
		) {
			const blockString = getBlockString(block);
			const args = {
				name: templateName,
				template_name: templateName,
				block: blockString,
			} as BlockTemplate;
			if (builderBlockTemplate.getRow(templateName)) {
				await builderBlockTemplate.setValue.submit(args);
			} else {
				args["category"] = category;
				args["preview"] = previewImage;
				await builderBlockTemplate.insert.submit(args);
			}
			toast.success("Block template saved!");
		},
		editOnCanvas(
			block: Block,
			saveAction: (block: Block) => void,
			saveActionLabel: string = "Save",
			fragmentName?: string,
		) {
			this.fragmentData = {
				block,
				saveAction,
				saveActionLabel,
				fragmentName: fragmentName || block.getBlockDescription(),
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
			};
		},
	},
});

export default useStore;
