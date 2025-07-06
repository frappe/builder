import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { BuilderPage } from "@/types/Builder/BuilderPage";

import {
	copyToClipboard,
	detachBlockFromComponent,
	getBlockCopy,
	getBlockInstance,
	getCopyWithoutParent,
	isJSONString,
	showDialog,
} from "@/utils/helpers";
import { createListResource } from "frappe-ui";
import { nextTick } from "vue";
import { toast } from "vue-sonner";
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

	const blocks = (
		copyEntirePage
			? [canvasStore.activeCanvas?.getRootBlock()]
			: canvasStore.activeCanvas?.selectedBlocks ?? []
	) as Block[];

	const componentDocuments: BuilderComponent[] = [];
	const blocksToCopy = blocks.map((block) => {
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
	});

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
	copyEntirePage && toast.success("Page Copied");
}

export async function pasteBuilderBlocks(e: ClipboardEvent, currentSiteURL: string): Promise<void> {
	const data = e.clipboardData?.getData("builder-copied-blocks") as string;
	if (!data || !isJSONString(data)) return;

	const clipboardData = JSON.parse(data) as BuilderClipboardData;
	const crossSitePaste = Boolean(clipboardData.sourceURL && clipboardData.sourceURL !== currentSiteURL);

	if (clipboardData.pageDoc) {
		await handlePagePaste(clipboardData, crossSitePaste, currentSiteURL);
	} else {
		if (clipboardData.components.length) {
			toast.loading("Pasting...", {
				id: "paste-blocks",
			});
			await handleComponents(clipboardData, crossSitePaste);
		}
		await insertBlocks(clipboardData.blocks);
		clipboardData.components.length &&
			toast.success("Done", {
				id: "paste-blocks",
			});
	}
}

async function handlePagePaste(
	clipboardData: BuilderClipboardData,
	crossSitePaste: boolean,
	currentURL: string | undefined = undefined,
): Promise<void> {
	const canvasStore = useCanvasStore();
	const pageStore = usePageStore();

	await showDialog({
		title: "Pasting a page!",
		message:
			"You are about to paste a page with settings and scripts. Do you want to update the current page or create a new one?",
		actions: [
			{
				label: "Create New Page",
				variant: "solid",
				async onClick() {
					toast.loading("Pasting...", { id: "paste-page" });
					await handleComponents(clipboardData, crossSitePaste);
					await handlePageScripts(clipboardData, currentURL || "");
					if (clipboardData.pageDoc) {
						clipboardData.pageDoc.blocks = clipboardData.blocks.map((block) => getCopyWithoutParent(block));
					}
					const newPage = await webPages.insert.submit(clipboardData.pageDoc);
					window.location.href = `/builder/page/${encodeURIComponent(newPage.name)}`;
					await pageStore.setPage(newPage.name);
					toast.success("Done", { id: "paste-page" });
				},
			},
			{
				label: "Update Current Page",
				variant: "subtle",
				async onClick() {
					toast.loading("Pasting...", { id: "paste-page" });
					await handleComponents(clipboardData, crossSitePaste);
					await handlePageScripts(clipboardData, currentURL || "");
					const currentPage = pageStore.activePage as BuilderPage;
					await webPages.setValue.submit({
						...clipboardData.pageDoc,
						name: currentPage.name,
					});
					await pageStore.setPage(currentPage.name);
					nextTick(() => {
						canvasStore.pushBlocks(clipboardData.blocks);
						pageStore.savePage();
					});
					toast.success("Done", { id: "paste-page" });
				},
			},
		],
		size: "md",
	});
}

async function handleComponents(clipboardData: BuilderClipboardData, crossSitePaste: boolean) {
	const componentStore = useComponentStore();
	const componentIdMap = new Map<string, string>();
	let { blocks } = clipboardData;

	for (const component of clipboardData.components) {
		delete component.for_web_page;

		if (crossSitePaste) {
			const originalId = component.name;
			const newId = generateHash(originalId, clipboardData.sourceURL || "");
			componentIdMap.set(originalId, newId);
			component.name = newId;
			component.component_id = newId;
			await componentStore.createComponent(component, true);
		} else {
			await componentStore.createComponent(component, false);
		}
	}

	if (crossSitePaste) {
		blocks.map((block) => {
			updateBlockComponentReferences(block, componentIdMap);
			const blockCopy = getBlockInstance(block);
			updateURLsInBlock(blockCopy, clipboardData.sourceURL as string);
			return blockCopy;
		});
	}
}

async function insertBlocks(blocks: (Block | BlockOptions)[]) {
	const canvasStore = useCanvasStore();
	if (canvasStore.activeCanvas?.selectedBlocks.length && blocks[0].blockId !== "root") {
		let parentBlock = canvasStore.activeCanvas.selectedBlocks[0];
		while (parentBlock && !parentBlock.canHaveChildren()) {
			parentBlock = parentBlock.getParentBlock() as Block;
		}
		blocks.forEach((block) => parentBlock.addChild(getBlockCopy(block), null, true));
	} else {
		canvasStore.pushBlocks(blocks);
	}
}

async function handlePageScripts(clipboardData: BuilderClipboardData, currentSiteURL: string): Promise<void> {
	if (!clipboardData.pageDoc || !clipboardData.sourceURL || clipboardData.sourceURL === currentSiteURL) {
		return;
	}

	const pageScriptIdMap = new Map<string, string>();
	for (const script of clipboardData.pageScripts || []) {
		const newScriptId = generateHash(script.name, clipboardData.sourceURL, true);
		pageScriptIdMap.set(script.name, newScriptId);

		const scriptDoc: BuilderClientScriptDocument = {
			...script,
			name: newScriptId,
		};

		const clientScriptResource = createListResource({
			doctype: "Builder Client Script",
		});
		try {
			await clientScriptResource.insert.submit(scriptDoc);
		} catch (error: { response?: { status: number } } | any) {
			if (error?.response?.status === 409) {
				// If script already exists, update it
				await clientScriptResource.setValue.submit(scriptDoc);
			} else {
				console.error("Error inserting client script:", error);
			}
			// pass
		}

		const clientScript = clipboardData.pageDoc.client_scripts?.find((s) => s.builder_script === script.name);
		if (clientScript) {
			clientScript.builder_script = newScriptId;
		}
	}
}

function updateBlockComponentReferences(block: BlockOptions, componentIdMap: Map<string, string>): void {
	if (!componentIdMap.size) return;
	if (block.extendedFromComponent && componentIdMap.has(block.extendedFromComponent)) {
		block.extendedFromComponent = componentIdMap.get(block.extendedFromComponent);
	}
	if (block.isChildOfComponent && componentIdMap.has(block.isChildOfComponent)) {
		block.isChildOfComponent = componentIdMap.get(block.isChildOfComponent);
	}

	block.children?.forEach((child) => updateBlockComponentReferences(child, componentIdMap));
}

function updateURLsInBlock(block: Block, currentSiteURL: string): void {
	// Update image and video sources to absolute URLs
	if (block.isImage() || block.isVideo()) {
		const src = block.getAttribute("src");
		if (src && typeof src === "string" && src.startsWith("/")) {
			block.setAttribute("src", `${currentSiteURL}${src}`);
		}
	}

	// Update background image URLs
	if (block) {
		const bgSrc = block.getStyle("backgroundImage");
		if (bgSrc && typeof bgSrc === "string" && bgSrc.startsWith("url(")) {
			const urlMatch = bgSrc.match(/url\(["']?([^"']+)["']?\)/);
			if (urlMatch && urlMatch[1] && urlMatch[1].startsWith("/")) {
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

function generateHash(initialId: string, siteURL: string, appendHash = false): string {
	if (!appendHash) {
		// Original behavior: Generate a deterministic hash with the same length as initialId
		const str = `${initialId}_${siteURL}`;
		let hash = 5381;
		for (let i = 0; i < str.length; i++) {
			hash = (hash << 5) + hash + str.charCodeAt(i); // djb2 hash
		}
		const hashStr = Math.abs(hash).toString(36);
		const targetLength = initialId.length;
		return hashStr.repeat(Math.ceil(targetLength / hashStr.length)).slice(0, targetLength);
	} else {
		// New behavior: Retain initialId and append a short hash
		const str = `${initialId}_${siteURL}`;
		let hash = 5381;
		for (let i = 0; i < str.length; i++) {
			hash = (hash << 5) + hash + str.charCodeAt(i);
		}
		const shortHash = Math.abs(hash).toString(36).slice(0, 8);
		return `${initialId}_${shortHash}`;
	}
}
