import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import blockController from "@/utils/blockController";

import {
	copyToClipboard,
	detachBlockFromComponent,
	getBlockCopy,
	getBlockInstance,
	getCopyWithoutParent,
	isJSONString,
	showDialog,
} from "@/utils/helpers";
import { nextTick } from "vue";
import { webPages } from "../data/webPage";
import { BuilderClientScript } from "../types/Builder/BuilderClientScript";

type BuilderPageClientScriptRef = { builder_script: string; idx?: number };

type BuilderPageSettings = Pick<
	BuilderPage,
	| "page_name"
	| "route"
	| "dynamic_route"
	| "is_template"
	| "template_name"
	| "page_data_script"
	| "head_html"
	| "body_html"
	| "page_title"
	| "meta_description"
	| "meta_image"
	| "canonical_url"
	| "authenticated_access"
	| "disable_indexing"
	| "favicon"
	| "blocks"
> & {
	client_scripts?: BuilderPageClientScriptRef[];
};

interface BuilderClipboardData {
	blocks: (Block | BlockOptions)[];
	components: BuilderComponent[];
	sourceURL?: string;
	pageDoc?: BuilderPageSettings;
	pageScripts?: BuilderClientScript[];
}

type BuilderClientScriptDocument = Partial<BuilderClientScript>;

function generateHash(componentId: string, siteURL: string): string {
	// Generate a deterministic hash with the same length as componentId, using siteURL for uniqueness
	const str = `${componentId}_${siteURL}`;
	let hash = 5381;
	for (let i = 0; i < str.length; i++) {
		hash = (hash << 5) + hash + str.charCodeAt(i); // djb2 hash
	}
	const hashStr = Math.abs(hash).toString(36);
	// Pad or trim the hash to match the original componentId length
	const targetLength = componentId.length;
	const padded = hashStr.repeat(Math.ceil(targetLength / hashStr.length)).slice(0, targetLength);
	return padded;
}

function updateURLsInBlock(block: Block, currentSiteURL: string): void {
	// Update image and video sources to absolute URLs
	if (block.isImage() || block.isVideo()) {
		const src = block.getAttribute("src");
		if (src && typeof src === "string" && !src.startsWith("http")) {
			block.setAttribute("src", `${currentSiteURL}${src}`);
		}
	}

	// Update background image URLs
	if (block) {
		const bgSrc = block.getStyle("backgroundImage");
		if (bgSrc && typeof bgSrc === "string" && bgSrc.startsWith("url(")) {
			const urlMatch = bgSrc.match(/url\(["']?([^"']+)["']?\)/);
			if (urlMatch && urlMatch[1] && !urlMatch[1].startsWith("http")) {
				block.setStyle("backgroundImage", `url(${currentSiteURL}${urlMatch[1]})`);
			}
		}
	}

	// Update href attributes for links
	// if (block.isLink()) {
	// 	const href = block.getAttribute("href");
	// 	if (href && typeof href === "string" && !href.startsWith("http") && !href.startsWith("#")) {
	// 		block.setAttribute("href", `${currentSiteURL}${href}`);
	// 	}
	// }

	// Recursively process children
	block.children.forEach((child) => updateURLsInBlock(child, currentSiteURL));
}

export function copyBuilderBlocks(
	e: ClipboardEvent,
	currentSiteURL: string,
	copyEntirePage: boolean = false,
) {
	const canvasStore = useCanvasStore();
	const componentStore = useComponentStore();
	const pageStore = usePageStore();
	if (!canvasStore.activeCanvas?.selectedBlocks.length && !copyEntirePage) return;
	e.preventDefault();

	const componentDocuments: BuilderComponent[] = [];
	const blocksToCopy =
		canvasStore.activeCanvas?.selectedBlocks.map((block) => {
			// Collect all used components
			const components = block.getUsedComponentNames();
			for (const componentName of components) {
				const component = componentStore.getComponent(componentName);
				if (component) {
					componentDocuments.push(component);
				}
			}

			// Handle component children and create copy
			let blockCopy = null;
			if (!Boolean(block.extendedFromComponent) && block.isChildOfComponent) {
				blockCopy = detachBlockFromComponent(block, null);
			} else {
				blockCopy = getCopyWithoutParent(block);
			}

			return blockCopy;
		}) || [];

	const dataToCopy: BuilderClipboardData = {
		blocks: blocksToCopy,
		components: componentDocuments,
		sourceURL: currentSiteURL,
	};

	if (copyEntirePage) {
		const currentPage = pageStore.activePage as BuilderPage;
		dataToCopy.pageDoc = {
			page_name: currentPage.page_name,
			route: currentPage.route,
			dynamic_route: currentPage.dynamic_route,
			page_data_script: currentPage.page_data_script,
			head_html: currentPage.head_html,
			body_html: currentPage.body_html,
			page_title: currentPage.page_title,
			meta_description: currentPage.meta_description,
			meta_image: currentPage.meta_image,
			authenticated_access: currentPage.authenticated_access,
			disable_indexing: currentPage.disable_indexing,
			favicon: currentPage.favicon,
			client_scripts:
				currentPage.client_scripts?.map((script) => {
					return {
						builder_script: script.builder_script,
						idx: script.idx,
					};
				}) || [],
		};
		dataToCopy.pageScripts = pageStore.activePageScripts;
	}
	copyToClipboard(dataToCopy, e, "builder-copied-blocks");
}

export async function pasteBuilderBlocks(e: ClipboardEvent, currentSiteURL: string): Promise<void> {
	const componentStore = useComponentStore();
	const canvasStore = useCanvasStore();
	const pageStore = usePageStore();

	const data = e.clipboardData?.getData("builder-copied-blocks") as string;
	if (!data || !isJSONString(data)) return;

	const clipboardData = JSON.parse(data) as BuilderClipboardData;
	const componentIdMap = new Map<string, string>();
	const isPagePaste = Boolean(clipboardData.pageDoc);
	let blocks = clipboardData.blocks;
	const crossSitePaste = clipboardData.sourceURL && clipboardData.sourceURL !== currentSiteURL;
	const isCanvasEmpty = !canvasStore.activeCanvas?.getRootBlock().children.length;

	if (isPagePaste && crossSitePaste) {
		// update pageScript name
		const pageScriptIdMap = new Map<string, string>();
		for (const script of clipboardData.pageScripts || []) {
			const newScriptId = generateHash(script.name, clipboardData.sourceURL || "");
			// maintain map
			pageScriptIdMap.set(script.name, newScriptId);
			const scriptDoc: BuilderClientScriptDocument = {
				...script,
				name: newScriptId,
			};

			const clientScript =
				clipboardData.pageDoc && clipboardData.pageDoc.client_scripts
					? clipboardData.pageDoc.client_scripts.find((s) => s.builder_script === script.name)
					: undefined;
			if (clientScript) {
				console.log("Updating client script reference:", clientScript.builder_script, "to", newScriptId);
				clientScript.builder_script = newScriptId;
			}
		}
	}

	if (crossSitePaste) {
		// Update component IDs and references (to avoid conflicts & overwrites in the current site)
		for (const component of clipboardData.components) {
			const originalId = component.name;
			const newId = generateHash(originalId, clipboardData.sourceURL || "");
			componentIdMap.set(originalId, newId);

			component.name = newId;
			component.component_id = newId;
			delete component.for_web_page;

			// Create new component with updated ID
			await componentStore.createComponent(component, true);
		}

		// Update block references to components
		for (const block of blocks) {
			if (block.extendedFromComponent && componentIdMap.has(block.extendedFromComponent)) {
				block.extendedFromComponent = componentIdMap.get(block.extendedFromComponent);
			}
			if (block.isChildOfComponent && componentIdMap.has(block.isChildOfComponent)) {
				block.isChildOfComponent = componentIdMap.get(block.isChildOfComponent);
			}
			// Handle nested blocks recursively
			updateBlockComponentReferences(block, componentIdMap);
		}

		blocks = blocks.map((block) => {
			const blockCopy = getBlockInstance(block);
			updateURLsInBlock(blockCopy, clipboardData.sourceURL as string);
			return blockCopy;
		});
	} else if (!clipboardData.sourceURL) {
		// Same site paste - just create components
		for (const component of clipboardData.components) {
			delete component.for_web_page;
			await componentStore.createComponent(component, false);
		}
	}

	if (blockController.isBlockSelected() && !blockController.multipleBlocksSelected() && blocks.length === 1) {
		// handle SVG paste case
		const selectedBlock = blockController.getSelectedBlocks()[0];
		const copiedBlock = getBlockCopy(blocks[0]);
		if (selectedBlock.isSVG() && copiedBlock.isSVG()) {
			const svgBlock = copiedBlock;
			if (!svgBlock.innerHTML) return;
			const svgContent = new DOMParser()
				.parseFromString(svgBlock.innerHTML, "text/html")
				.body.querySelector("svg");
			if (svgContent) {
				svgContent.removeAttribute("width");
				svgContent.removeAttribute("height");
				selectedBlock.setInnerHTML(svgContent.outerHTML);
				return;
			}
		}
	}

	if (isPagePaste) {
		await showDialog({
			title: "Pasting a page!",
			message:
				"You are about to paste a page with settings and scripts. Do you want to update the current page or create a new one?",
			actions: [
				{
					label: "Create New Page",
					variant: "solid",
					async onClick() {
						if (clipboardData.pageDoc) {
							clipboardData.pageDoc.blocks = clipboardData.blocks.map((block) => {
								return getCopyWithoutParent(block);
							});
						}
						const newPage = await webPages.insert.submit(clipboardData.pageDoc);
						window.location.href = `/builder/page/${encodeURIComponent(newPage.name)}`;
					},
				},
				{
					label: "Update Current Page",
					variant: "subtle",
					async onClick() {
						const currentPage = pageStore.activePage as BuilderPage;
						await webPages.setValue.submit({
							...clipboardData.pageDoc,
							name: currentPage.name,
						});
						await pageStore.setPage(currentPage.name);
						nextTick(() => {
							canvasStore.pushBlocks(blocks);
							pageStore.savePage();
						});
					},
				},
			],
			size: "md",
		});
	} else {
		if (canvasStore.activeCanvas?.selectedBlocks.length && blocks[0].blockId !== "root") {
			let parentBlock = canvasStore.activeCanvas.selectedBlocks[0];
			while (parentBlock && !parentBlock.canHaveChildren()) {
				parentBlock = parentBlock.getParentBlock() as Block;
			}
			blocks.forEach((block: BlockOptions) => {
				parentBlock.addChild(getBlockCopy(block), null, true);
			});
		} else {
			canvasStore.pushBlocks(blocks);
		}
	}
}

function updateBlockComponentReferences(block: BlockOptions, componentIdMap: Map<string, string>): void {
	if (block.extendedFromComponent && componentIdMap.has(block.extendedFromComponent)) {
		block.extendedFromComponent = componentIdMap.get(block.extendedFromComponent);
	}
	if (block.isChildOfComponent && componentIdMap.has(block.isChildOfComponent)) {
		block.isChildOfComponent = componentIdMap.get(block.isChildOfComponent);
	}

	block.children?.forEach((child) => updateBlockComponentReferences(child, componentIdMap));
}
