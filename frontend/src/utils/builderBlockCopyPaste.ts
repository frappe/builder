import { __ } from "@/translation";
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderClientScript, BuilderComponent, BuilderPage, BuilderToken } from "@/types/doctypes";

import builderTokens from "@/data/builderToken";
import {
	collectRemoteAssets,
	dropImportedFontFaces,
	importRemoteAssets,
	importRemoteFonts,
	type RemoteFont,
} from "@/utils/importRemoteAssets";
import {
	copyToClipboard,
	detachBlockFromComponent,
	getBlockCopy,
	getBlockInstance,
	getCopyWithoutParent,
	isJSONString,
	showDialog,
} from "@/utils/helpers";
import { createListResource, toast } from "frappe-ui";
import { nextTick } from "vue";
import { webPages } from "../data/webPage";

type BuilderPageClientScriptRef = { builder_script: string; idx?: number };

// pre-rename sites use variable_name where Builder Token uses token_name
type LegacyAwareToken = BuilderToken & { variable_name?: string };

type BuilderPageSettings = Pick<
	BuilderPage,
	| "page_name"
	| "route"
	| "dynamic_route"
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
	variables?: LegacyAwareToken[];
	sourceURL?: string;
	pageDoc?: BuilderPageSettings;
	pageScripts?: BuilderClientScript[];
	fonts?: RemoteFont[];
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
			: (canvasStore.activeCanvas?.selectedBlocks ?? [])
	) as Block[];

	const componentDocuments: BuilderComponent[] = [];
	const variableNames = new Set<string>();
	const blocksToCopy = blocks.map((block) => {
		// Collect all used components
		const components = block.getUsedComponentNames();
		for (const componentName of components) {
			const component = componentStore.getComponent(componentName);
			if (component) {
				componentDocuments.push(component);
			}
		}

		const variables = block.getUsedVariableNames();
		for (const variableName of variables) {
			variableNames.add(variableName);
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

	const variableDocuments: LegacyAwareToken[] = [];
	for (const variableName of variableNames) {
		const variable = builderTokens.data?.find((v: BuilderToken) => v.name === variableName);
		if (variable) {
			// variable_name keeps the clipboard readable by sites on the pre-rename schema
			variableDocuments.push({ ...variable, variable_name: variable.token_name });
		}
	}

	const dataToCopy: BuilderClipboardData = {
		blocks: blocksToCopy,
		components: componentDocuments,
		variables: variableDocuments,
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
	copyEntirePage && toast.success(__("Page Copied"));
}

/**
 * The "builder-copied-blocks" clipboard type and the shape below are a public
 * contract: the Copy to Frappe Builder browser extension writes this payload from
 * any web page (github.com/surajshetty3416/copy-to-builder, see its CONTRACT.md).
 * Adding keys is safe, renaming or removing the ones it writes is not.
 */
export async function pasteBuilderBlocks(e: ClipboardEvent, currentSiteURL: string): Promise<void> {
	const data = e.clipboardData?.getData("builder-copied-blocks") as string;
	if (!data || !isJSONString(data)) return;

	const clipboardData = JSON.parse(data) as BuilderClipboardData;
	const crossSitePaste = Boolean(clipboardData.sourceURL && clipboardData.sourceURL !== currentSiteURL);

	if (clipboardData.pageDoc) {
		await handlePagePaste(clipboardData, crossSitePaste, currentSiteURL);
	} else {
		const hasDependencies = Boolean(clipboardData.components?.length || clipboardData.variables?.length);
		if (hasDependencies) {
			toast.loading(__("Pasting..."), {
				id: "paste-blocks",
			});
			await handleDependencies(clipboardData, crossSitePaste);
		}
		await insertBlocks(clipboardData.blocks);
		await handlePageScripts(clipboardData, currentSiteURL);
		hasDependencies &&
			toast.success(__("Done"), {
				id: "paste-blocks",
			});
		offerRemoteAssetImport(crossSitePaste, clipboardData.fonts || []);
	}
}

const PENDING_ASSET_IMPORT = "builder:pending-asset-import";

// Pasting a whole page reloads the editor on the new page, so the offer is left
// behind for the editor to pick up once it has the page open.
export function offerPendingAssetImport(pageName: string) {
	const pending = sessionStorage.getItem(PENDING_ASSET_IMPORT);
	if (!pending) return;
	sessionStorage.removeItem(PENDING_ASSET_IMPORT);
	if (!isJSONString(pending)) return;

	const { page, fonts } = JSON.parse(pending) as { page: string; fonts: RemoteFont[] };
	if (page !== pageName) return;
	offerRemoteAssetImport(true, fonts);
}

// Images and webfonts in a cross-site paste still load from the site they came from.
// Pasting stays fast by leaving them alone, and the import is offered right after so
// the page can be made self contained in one click.
function offerRemoteAssetImport(crossSitePaste: boolean, fonts: RemoteFont[] = []) {
	if (!crossSitePaste) return;
	const canvasStore = useCanvasStore();
	const pageStore = usePageStore();
	const root = canvasStore.activeCanvas?.getRootBlock();
	if (!root) return;

	const urls = collectRemoteAssets([root]);
	if (!urls.length && !fonts.length) return;

	const parts = [];
	if (urls.length) parts.push(`${urls.length} ${urls.length === 1 ? "image" : "images"}`);
	if (fonts.length) parts.push(`${fonts.length} ${fonts.length === 1 ? "font" : "fonts"}`);

	toast.info(`${parts.join(" and ")} still load from the original site`, {
		duration: 15000,
		action: {
			label: "Import to this site",
			onClick: async () => {
				if (urls.length) await importRemoteAssets([root], urls);
				const imported = fonts.length ? await importRemoteFonts(fonts) : {};
				await dropRemoteFontFaces(Object.keys(imported));
				pageStore.savePage();
			},
		},
	});
}

// With the families now living here, the copied @font-face rules in the page head
// would override them once published.
async function dropRemoteFontFaces(families: string[]) {
	const pageStore = usePageStore();
	const page = pageStore.activePage as BuilderPage;
	if (!families.length || !page?.head_html) return;

	const headHtml = dropImportedFontFaces(page.head_html, families);
	if (headHtml === page.head_html) return;
	await webPages.setValue.submit({ name: page.name, head_html: headHtml });
	page.head_html = headHtml;
}

// Tokens first: their ids are rewritten inside the blocks and inside the component
// blocks that are about to be saved, so a cross-site paste keeps its var() refs alive.
async function handleDependencies(
	clipboardData: BuilderClipboardData,
	crossSitePaste: boolean,
): Promise<void> {
	if (clipboardData.variables?.length) {
		await handleVariables(clipboardData, crossSitePaste);
	}
	if (clipboardData.components?.length) {
		await handleComponents(clipboardData, crossSitePaste);
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
		title: __("Pasting a page!"),
		message: __("You are about to paste a page with settings and scripts. Do you want to update the current page or create a new one?"),
		actions: [
			{
				label: __("Create New Page"),
				variant: "subtle",
				async onClick() {
					toast.loading(__("Pasting..."), { id: "paste-page" });
					await handleDependencies(clipboardData, crossSitePaste);
					await handlePageScripts(clipboardData, currentURL || "");
					if (clipboardData.pageDoc) {
						clipboardData.pageDoc.blocks = clipboardData.blocks.map((block) => getCopyWithoutParent(block));
					}
					const newPage = await webPages.insert.submit(clipboardData.pageDoc);
					if (crossSitePaste) {
						sessionStorage.setItem(
							PENDING_ASSET_IMPORT,
							JSON.stringify({ page: newPage.name, fonts: clipboardData.fonts || [] }),
						);
					}
					window.location.href = `/builder/page/${encodeURIComponent(newPage.name)}`;
					await pageStore.setPage(newPage.name);
					toast.success(__("Done"), { id: "paste-page" });
				},
			},
			{
				label: __("Update Current Page"),
				variant: "solid",
				async onClick() {
					toast.loading(__("Pasting..."), { id: "paste-page" });
					await handleDependencies(clipboardData, crossSitePaste);
					await handlePageScripts(clipboardData, currentURL || "");
					const currentPage = pageStore.activePage as BuilderPage;
					await webPages.setValue.submit({
						...clipboardData.pageDoc,
						name: currentPage.name,
					});
					await pageStore.setPage(currentPage.name);
					nextTick(() => {
						canvasStore.pushBlocks(clipboardData.blocks, false);
						pageStore.savePage();
						offerRemoteAssetImport(crossSitePaste, clipboardData.fonts || []);
					});
					toast.success(__("Done"), { id: "paste-page" });
				},
			},
		],
		size: "md",
	});
}

// clipboards copied from a site on the pre-rename schema carry variable_name
function normalizeLegacyToken(variable: LegacyAwareToken): BuilderToken {
	if (!variable.token_name && variable.variable_name) {
		variable.token_name = variable.variable_name;
	}
	delete variable.variable_name;
	return variable;
}

async function handleVariables(clipboardData: BuilderClipboardData, crossSitePaste: boolean) {
	const idMap = new Map<string, string>();
	for (const variable of (clipboardData.variables || []).map(normalizeLegacyToken)) {
		if (crossSitePaste) {
			const originalName = variable.name;
			// a token id is assigned by the server, so reuse an equivalent token when
			// there is one and otherwise map the refs to the id we actually get back
			const twin = builderTokens.data?.find(
				(v: BuilderToken) =>
					v.token_name === variable.token_name && v.value === variable.value && v.type === variable.type,
			);
			let newName = twin?.name;
			if (!newName) {
				try {
					newName = (await builderTokens.insert.submit(variable))?.name;
				} catch (error: any) {
					console.error("Error inserting token:", error);
				}
			}
			if (newName && newName !== originalName) {
				idMap.set(originalName, newName);
			}
		} else {
			const existing = builderTokens.data?.find((v: BuilderToken) => v.name === variable.name);
			if (!existing) {
				try {
					await builderTokens.insert.submit(variable);
				} catch (error: any) {
					if (error?.response?.status !== 409) {
						console.error("Error inserting variable:", error);
					}
				}
			}
		}
	}
	if (crossSitePaste && idMap.size) {
		clipboardData.blocks.forEach((block) => rewriteVariableRefsInBlock(block as BlockOptions, idMap));
		clipboardData.components?.forEach((component) => rewriteVariableRefsInComponent(component, idMap));
	}
}

// A component travels with its own copy of its block tree, so the token ids inside
// it need the same rewrite the pasted blocks get.
function rewriteVariableRefsInComponent(component: BuilderComponent, idMap: Map<string, string>) {
	if (!component.block) return;
	const isString = typeof component.block === "string";
	let block: BlockOptions;
	try {
		block = isString ? JSON.parse(component.block as string) : component.block;
	} catch (error) {
		return;
	}
	rewriteVariableRefsInBlock(block, idMap);
	component.block = isString ? JSON.stringify(block) : block;
}

function rewriteVariableRefsInBlock(block: BlockOptions, idMap: Map<string, string>) {
	if (!idMap.size) return;
	const pattern = new RegExp(
		`var\\(--(${Array.from(idMap.keys())
			.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
			.join("|")})(?=[,\\s)])`,
		"g",
	);
	const rewrite = (value: unknown): unknown => {
		if (typeof value !== "string" || !value.includes("var(--")) return value;
		return value.replace(pattern, (_match, name) => `var(--${idMap.get(name)}`);
	};
	const rewriteObj = (obj: Record<string, unknown> | undefined | null) => {
		if (!obj) return;
		for (const key of Object.keys(obj)) {
			obj[key] = rewrite(obj[key]);
		}
	};
	rewriteObj(block.baseStyles as Record<string, unknown> | undefined);
	rewriteObj(block.mobileStyles as Record<string, unknown> | undefined);
	rewriteObj(block.tabletStyles as Record<string, unknown> | undefined);
	rewriteObj(block.attributes as Record<string, unknown> | undefined);
	if (block.innerHTML) block.innerHTML = rewrite(block.innerHTML) as string;
	block.children?.forEach((child) => rewriteVariableRefsInBlock(child, idMap));
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
		canvasStore.pushBlocks(
			blocks.map((block) => getBlockCopy(block)),
			false,
		);
	}
}

async function handlePageScripts(clipboardData: BuilderClipboardData, currentSiteURL: string): Promise<void> {
	if (!clipboardData.sourceURL || clipboardData.sourceURL === currentSiteURL) {
		return;
	}
	if (!clipboardData.pageScripts?.length) return;

	const pageScriptIdMap = new Map<string, string>();
	const insertedScripts: BuilderClientScriptDocument[] = [];
	for (const script of clipboardData.pageScripts || []) {
		const newScriptId = generateHash(script.name, clipboardData.sourceURL, true);
		pageScriptIdMap.set(script.name, newScriptId);

		const scriptDoc: BuilderClientScriptDocument = {
			...script,
			name: newScriptId,
		};
		insertedScripts.push(scriptDoc);

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

		const clientScript = clipboardData.pageDoc?.client_scripts?.find((s) => s.builder_script === script.name);
		if (clientScript) {
			clientScript.builder_script = newScriptId;
		}
	}

	// Pasting blocks rather than a whole page still needs somewhere for the styles
	// they depend on to live, so they attach to the page being pasted into.
	if (!clipboardData.pageDoc) {
		await attachScriptsToCurrentPage(insertedScripts);
	}
}

async function attachScriptsToCurrentPage(scripts: BuilderClientScriptDocument[]): Promise<void> {
	const pageStore = usePageStore();
	const currentPage = pageStore.activePage as BuilderPage;
	if (!currentPage || !scripts.length) return;

	const existing = (currentPage.client_scripts || []).map((script) => script.builder_script);
	const missing = scripts.filter((script) => script.name && !existing.includes(script.name));
	if (!missing.length) return;

	const clientScripts = [...existing, ...missing.map((script) => script.name as string)].map((id) => ({
		builder_script: id,
	}));
	await webPages.setValue.submit({ name: currentPage.name, client_scripts: clientScripts });

	// keep the open editor in step without reloading the page and losing the paste
	currentPage.client_scripts = clientScripts as BuilderPage["client_scripts"];
	pageStore.activePageScripts = [...pageStore.activePageScripts, ...(missing as BuilderClientScript[])];
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

		if (block.isImage()) {
			const darkSrc = block.getAttribute("darkSrc");
			if (darkSrc && typeof darkSrc === "string" && darkSrc.startsWith("/")) {
				block.setAttribute("darkSrc", `${currentSiteURL}${darkSrc}`);
			}
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
