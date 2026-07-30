import Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { BuilderPage } from "@/types/doctypes";
import getBlockTemplate from "@/utils/blockTemplate";
import { dialog, FileUploadHandler, toast } from "frappe-ui";
import { reactive, toRaw } from "vue";
import { getRGB, HexToHSV, HSVToHex } from "./colors";
import {
	addPxToNumber,
	extractNumberAndUnit,
	getBoxSpacing,
	getNumberFromPx,
	normalizeValueWithUnits,
	parseAndSetBackground,
	removeDefaultUnit,
	setBoxSpacing,
	shortenNumber,
} from "./cssUtils";

function toTitleCase(str: string): string {
	return str.replace(/[_-]/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

async function confirm(message: string, title: string = "Confirm"): Promise<boolean> {
	return new Promise((resolve) => {
		showDialog({
			title,
			message,
			icon: {
				name: "alert-circle",
				appearance: "warning",
			},
			actions: [
				{
					label: "Cancel",
					variant: "subtle",
					onClick: () => resolve(false),
				},
				{
					label: "Confirm",
					theme: "red",
					onClick: () => resolve(true),
				},
			],
		});
	});
}

async function alert(message: string, title: string = "Alert"): Promise<boolean> {
	await showDialog({
		title,
		message,
		actions: [{ label: "Ok", variant: "solid", onClick: () => {} }],
	});
	return true;
}

function getTextContent(html: string | null) {
	if (!html || !isHTMLString(html)) {
		return html || "";
	}
	const tmp = document.createElement("div");
	tmp.innerHTML = html || "";
	const textContent = tmp.textContent || tmp.innerText || "";
	tmp.remove();
	return textContent;
}

function isHTMLString(str: string) {
	return /<[a-z][\s\S]*>/i.test(str);
}

function copyToClipboard(text: string | object, e: ClipboardEvent, copyFormat = "text/plain") {
	if (typeof text !== "string") {
		text = JSON.stringify(text);
	}
	e.clipboardData?.setData(copyFormat, text);
}

function findNearestSiblingIndex(e: MouseEvent) {
	let nearestElementIndex = 0;
	let minDistance = Number.MAX_VALUE;
	let parent = e.target as HTMLElement;

	const elements = Array.from(parent.children);
	elements.forEach(function (element, index) {
		const rect = element.getBoundingClientRect();
		const centerX = rect.left + rect.width / 2;
		const centerY = rect.top + rect.height / 2;

		const distance = Math.sqrt(Math.pow(centerX - e.clientX, 2) + Math.pow(centerY - e.clientY, 2));
		if (distance < minDistance) {
			minDistance = distance;
			nearestElementIndex = index;
			const positionBitmask = element.compareDocumentPosition(e.target as Node);
			// sourcery skip: possible-incorrect-bitwise-operator
			if (positionBitmask & Node.DOCUMENT_POSITION_PRECEDING) {
				// before
			} else {
				nearestElementIndex += 1;
			}
		}
	});
	return nearestElementIndex;
}

// converts border-color to borderColor
function kebabToCamelCase(str: string) {
	return str.replace(/-([a-z])/g, function (g) {
		return g[1].toUpperCase();
	});
}

function toKebabCase(str: string) {
	return str
		.replace(/([a-z])([A-Z])/g, "$1-$2")
		.replace(/([A-Z])([A-Z][a-z])/g, "$1-$2")
		.toLowerCase()
		.replace(/\s+/g, "-");
}

function normalizeCSSPropertyName(property: string | null | undefined) {
	return (property || "").trim().toLowerCase();
}

const INTERACTIVE_CONTROL_SELECTOR =
	"input, textarea, select, button, a, [role='button'], [contenteditable='true'], .form-input, [class~='group/autocomplete']";

// used to let control widgets keep their own click/contextmenu behaviour
function isInteractiveControl(target: EventTarget | null) {
	if (!(target instanceof HTMLElement)) return false;
	return Boolean(target.closest(INTERACTIVE_CONTROL_SELECTOR));
}

// splits an optional state prefix (hover:color) from the property name
function splitStylePrefix(style: string) {
	const separatorIndex = style.indexOf(":");
	if (separatorIndex === -1) return { prefix: "", property: style };
	return { prefix: style.slice(0, separatorIndex + 1), property: style.slice(separatorIndex + 1) };
}

// hover:border-color -> hover:borderColor
function toStyleProperty(cssProperty: string) {
	const { prefix, property } = splitStylePrefix(cssProperty);
	return `${prefix}${kebabToCamelCase(property)}` as styleProperty;
}

// hover:borderColor -> hover:border-color
function toCSSProperty(style: string) {
	const { prefix, property } = splitStylePrefix(style);
	return `${prefix}${toKebabCase(property)}`;
}

function stripStatePrefix(style: string) {
	return splitStylePrefix(style).property;
}

function isJSONString(str: string) {
	try {
		JSON.parse(str);
	} catch (e) {
		return false;
	}
	return true;
}

function isTargetEditable(e: Event) {
	const target = e.target as HTMLElement;
	const isEditable = target.isContentEditable;
	const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA";
	return isEditable || isInput;
}

function getDataForKey(datum: Object, key: string) {
	const data = Object.assign({}, datum);
	const value = key
		.split(".")
		.reduce(
			(d: Record<string, any> | null, key) => (d && typeof d === "object" ? d[key] : null),
			data as Record<string, any>,
		);
	return value;
}

function replaceMapKey(map: Map<any, any>, oldKey: string, newKey: string) {
	const newMap = new Map();
	map.forEach((value, key) => {
		if (key === oldKey) {
			newMap.set(newKey, value);
		} else {
			newMap.set(key, value);
		}
	});
	return newMap;
}

const mapToObject = (map: Map<any, any>) => Object.fromEntries(map.entries());

function getBlockInstance(options: BlockOptions | string, retainId = true): Block {
	if (typeof options === "string") {
		options = JSON.parse(options) as BlockOptions;
	}
	if (!retainId) {
		const deleteBlockId = (block: BlockOptions) => {
			delete block.blockId;
			for (let child of block.children || []) {
				deleteBlockId(child);
			}
		};
		deleteBlockId(options);
	}
	return reactive(new Block(options));
}

function getBlockCopy(block: BlockOptions | Block, retainId = false): Block {
	const b = getBlockObjectCopy(block);
	return getBlockInstance(b, retainId);
}

function isCtrlOrCmd(e: KeyboardEvent | MouseEvent) {
	return e.ctrlKey || e.metaKey;
}

const detachBlockFromComponent = (block: Block, componentId: null | string) => {
	if (!componentId) {
		componentId = block.extendedFromComponent as string;
	}
	const blockCopy = getBlockCopy(block, true);

	if (block.extendedFromComponent && block.extendedFromComponent != componentId) {
		return blockCopy;
	}

	const component = block.referenceComponent;
	blockCopy.element = block?.getElement();
	blockCopy.attributes = block.getAttributes();
	blockCopy.classes = block.getClasses();
	blockCopy.baseStyles = component?.baseStyles
		? { ...component.baseStyles, ...block.baseStyles }
		: block.baseStyles;
	blockCopy.mobileStyles = component?.mobileStyles
		? { ...component.mobileStyles, ...block.mobileStyles }
		: block.mobileStyles;
	blockCopy.tabletStyles = component?.tabletStyles
		? { ...component.tabletStyles, ...block.tabletStyles }
		: block.tabletStyles;
	blockCopy.customAttributes = component?.customAttributes
		? { ...component.customAttributes, ...block.customAttributes }
		: block.customAttributes;
	blockCopy.isRepeaterBlock = component?.isRepeaterBlock || block.isRepeaterBlock;
	blockCopy.visibilityCondition = component?.visibilityCondition || block.visibilityCondition;
	blockCopy.innerHTML = block.innerHTML || component?.innerHTML;
	blockCopy.props = Object.fromEntries(
		Object.entries(block.getBlockProps()).map(([key, prop]) => {
			const propCopy = { ...prop }; // creating copy to avoid mutating original prop
			if (propCopy.isStandard) {
				let value = propCopy.value || propCopy.propOptions?.options?.defaultValue;
				if (!["string", "select"].includes(propCopy.propOptions?.type!)) {
					propCopy.value = JSON.stringify(value);
				} else {
					propCopy.value = value;
				}
				propCopy.isStandard = false;
				propCopy.propOptions = undefined;
			}
			return [key, propCopy];
		}),
	);

	delete blockCopy.extendedFromComponent;
	delete blockCopy.componentVersion;
	delete blockCopy.isChildOfComponent;
	delete blockCopy.referenceBlockId;
	blockCopy.children = blockCopy.children.map((block) => detachBlockFromComponent(block, componentId));
	return getBlockInstance(blockCopy);
};

function getBlockString(block: BlockOptions | Block): string {
	return JSON.stringify(getCopyWithoutParent(block));
}

function getBlockObjectCopy(block: BlockOptions | Block): BlockOptions {
	return JSON.parse(getBlockString(block));
}

function getCopyWithoutParent(block: BlockOptions | Block): BlockOptions {
	const blockCopy = { ...toRaw(block) };
	blockCopy.children = blockCopy.children?.map((child) => getCopyWithoutParent(child));
	delete blockCopy.parentBlock;
	delete blockCopy.referenceComponent;
	if (!blockCopy.extendedFromComponent) {
		delete blockCopy.componentVersion;
	}
	return removeEmptyBlockValues(blockCopy);
}

function isEmptyValue(value: unknown): boolean {
	if (value === null || value === "") {
		return true;
	}
	if (Array.isArray(value)) {
		return value.length === 0;
	}
	if (value && typeof value === "object") {
		return Object.keys(value).length === 0;
	}
	return false;
}

const diffArray = <T>(src: T[] | undefined, oldComp: T[] | undefined): T[] => {
	const oldJson = new Set((oldComp || []).map((item) => JSON.stringify(item)));
	return (src || []).filter((item) => !oldJson.has(JSON.stringify(item)));
};

const deepEqual = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

function removeEmptyBlockValues(block: BlockOptions): BlockOptions {
	if (block.clientScript) {
		block.clientScript = { ...block.clientScript };
		for (const key of Object.keys(block.clientScript) as Array<keyof BlockClientScript>) {
			if (isEmptyValue(block.clientScript[key])) {
				delete block.clientScript[key];
			}
		}
	}
	for (const key of Object.keys(block)) {
		if (isEmptyValue(block[key])) {
			delete block[key];
		}
	}
	return block;
}

function getRouteVariables(route: string) {
	const variables = [] as string[];
	route.split("/").map((part) => {
		if (part.startsWith(":") && part.length > 1) {
			variables.push(part.slice(1));
		}
		if (part.startsWith("<") && part.length > 1) {
			variables.push(part.slice(1, -1));
		}
	});
	return variables;
}

async function uploadBuilderAsset(file: File, silent = false) {
	const uploader = new FileUploadHandler();
	let fileDoc = {
		file_url: "",
		file_name: "",
	};
	const upload = uploader.upload(file, {
		private: false,
		folder: "Home/Builder Uploads",
		upload_endpoint: "/api/method/builder.api.upload_builder_asset",
	});
	await new Promise((resolve) => {
		if (silent) {
			upload.then((data: { file_name: string; file_url: string }) => {
				fileDoc.file_name = data.file_name;
				fileDoc.file_url = data.file_url;
				resolve(fileDoc);
			});
			return;
		}
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
}

function dataURLtoFile(dataurl: string, filename: string) {
	try {
		let arr = dataurl.split(",");
		let mimeMatch = arr[0].match(/:(.*?)(;|,)/);
		let mime = mimeMatch ? mimeMatch[1] : "";
		let isBase64 = arr[0].includes(";base64");

		let dataString = arr.slice(1).join(",");
		let u8arr;

		if (isBase64) {
			let bstr = atob(dataString);
			let n = bstr.length;
			u8arr = new Uint8Array(n);
			while (n--) {
				u8arr[n] = bstr.charCodeAt(n);
			}
		} else {
			let decoded = decodeURIComponent(dataString);
			let n = decoded.length;
			u8arr = new Uint8Array(n);
			while (n--) {
				u8arr[n] = decoded.charCodeAt(n);
			}
		}

		return new File([u8arr], filename, { type: mime });
	} catch (error) {
		console.error(`Failed to convert dataURL ${dataurl.substring(0, 50)}... to file.`, error);
		return null;
	}
}

function handleBase64Attribute(block: Block, attrName: string, fileName: string) {
	const attrValue = block.getAttribute(attrName) as string;
	if (attrValue?.startsWith("data:image")) {
		const file = dataURLtoFile(attrValue, fileName);
		if (file) {
			block.setAttribute(attrName, "");
			uploadBuilderAsset(file, true).then((obj) => {
				block.setAttribute(attrName, obj.fileURL);
			});
		}
	}
}

declare global {
	interface Window {
		Module: {
			decompress: (arrayBuffer: ArrayBuffer) => Uint8Array;
			onRuntimeInitialized?: () => void;
		};
	}
}

// Lazily loads the wawoff2 wasm runtime (sets window.Module) and decompresses
// a woff2 buffer to raw font bytes; non-woff2 buffers are returned unchanged.
async function decompressFontIfWoff2(arrayBuffer: ArrayBuffer, isWoff2: boolean): Promise<ArrayBuffer> {
	if (!isWoff2) return arrayBuffer;
	if (!window.Module) {
		const loadScript = (src: string) =>
			new Promise((onload) =>
				document.documentElement.append(Object.assign(document.createElement("script"), { src, onload })),
			);
		const path = "https://unpkg.com/wawoff2@2.0.1/build/decompress_binding.js";
		// @ts-ignore - Module is populated by the wawoff2 runtime once initialized
		const init = new Promise((done) => (window.Module = { onRuntimeInitialized: done }));
		await loadScript(path).then(() => init);
	}
	return Uint8Array.from(window.Module.decompress(arrayBuffer)).buffer;
}

async function getFontNameFromFile(file: File): Promise<string> {
	const arrayBuffer = await file.arrayBuffer();
	const buffer = await decompressFontIfWoff2(arrayBuffer, file.name.endsWith(".woff2"));
	const opentype = await import("opentype.js");
	return opentype.parse(buffer).names.fullName.en;
}

type UploadUserFontOptions = {
	confirmBeforeUpload?: boolean;
};

type UploadUserFontResult = {
	uploaded: boolean;
	fontName: string;
	alreadyExists?: boolean;
};

async function uploadUserFont(
	file: File,
	options: UploadUserFontOptions = {},
): Promise<UploadUserFontResult | null> {
	const { default: userFont } = await import("@/data/userFonts");

	const fontName = await getFontNameFromFile(file);

	// Check if font already exists
	const existingFont = userFont.data?.find((f: { font_name: string }) => f.font_name === fontName);

	if (existingFont) {
		toast.info(`Font "${fontName}" already exists in the project`);
		return { uploaded: false, fontName, alreadyExists: true };
	}

	// Confirm before uploading if requested
	if (options.confirmBeforeUpload) {
		const confirmed = await confirm(`Do you want to upload the font "${fontName}"?`, "Upload Font");
		if (!confirmed) {
			return null;
		}
	}

	const uploadPromise = (async (): Promise<UploadUserFontResult> => {
		const fileUploadHandler = new FileUploadHandler();
		const uploadedFile = await fileUploadHandler.upload(file, {
			private: false,
			folder: "Home/Builder Uploads/Fonts",
		});

		// Load the font
		const fontFace = new FontFace(fontName, `url("${uploadedFile.file_url}")`);
		const loadedFont = await fontFace.load();
		document.fonts.add(loadedFont);

		// Save to User Font doctype
		try {
			await userFont.insert.submit({
				font_name: fontName,
				font_file: uploadedFile.file_url,
			});
		} catch (e: any) {
			if (!e?.message?.includes("DuplicateEntryError")) {
				throw e;
			}
		}

		await userFont.fetch();
		return { uploaded: true, fontName };
	})();

	toast.promise(uploadPromise, {
		loading: "Uploading font...",
		success: `Font "${fontName}" uploaded successfully`,
		error: "Failed to upload font",
	});

	return uploadPromise;
}

function generateId() {
	return Math.random().toString(36).slice(2, 11);
}

function isBlock(e: MouseEvent) {
	return (
		(e.target instanceof HTMLElement || e.target instanceof SVGElement) &&
		e.target.closest(".__builder_component__")
	);
}

type BlockInfo = {
	blockId: string;
	breakpoint: string;
};

function getBlockInfo(e: MouseEvent) {
	const target = (e.target as HTMLElement)?.closest(".__builder_component__") as HTMLElement;
	return target.dataset as BlockInfo;
}

function getBlock(e: MouseEvent) {
	const canvasStore = useCanvasStore();
	const blockInfo = getBlockInfo(e);
	return canvasStore.activeCanvas?.findBlock(blockInfo.blockId);
}

function getRootBlockTemplate() {
	return getBlockInstance(getBlockTemplate("body"));
}

function getImageBlock(imageSrc: string, imageAlt: string = "") {
	const imageBlock = getBlockTemplate("image");
	if (!imageBlock.attributes) {
		imageBlock.attributes = {};
	}
	imageBlock.attributes.src = imageSrc;
	return imageBlock;
}

function getVideoBlock(videoSrc: string) {
	const videoBlock = getBlockTemplate("video");
	if (!videoBlock.attributes) {
		videoBlock.attributes = {};
	}
	videoBlock.attributes.src = videoSrc;
	return videoBlock;
}

function openInDesk(page: BuilderPage) {
	window.open(`/app/builder-page/${page.page_name}`, "_blank");
}

// quote the URL so that file names with spaces or special characters stay valid CSS
const cssUrl = (url: string) => `url("${url.replace(/"/g, '\\"')}")`;

interface DialogAction {
	label: string;
	variant?: "solid" | "subtle" | "outline" | "ghost";
	theme?: "gray" | "blue" | "green" | "red";
	onClick?: () => void | Promise<void>;
}

interface DialogOptions {
	title?: string;
	message: string;
	icon?: {
		name: string;
		appearance?: "warning" | "info" | "danger" | "success";
	};
	actions?: DialogAction[];
	size?: "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl" | "5xl" | "6xl" | "7xl";
}

function showDialog(options: DialogOptions): Promise<void> {
	const appearanceToTheme = { warning: "yellow", info: "blue", danger: "red", success: "green" } as const;
	return new Promise((resolve) => {
		dialog.confirm({
			title: options.title || "",
			message: options.message,
			size: options.size || "md",
			actions: (options.actions || []).map((action) => ({
				label: action.label,
				variant: action.variant ?? "subtle",
				theme: action.theme ?? "gray",
				onClick: async ({ close }) => {
					if (action.onClick) await action.onClick();
					close();
					resolve();
				},
			})),
			onCancel: () => resolve(),
			...(options.icon
				? { icon: options.icon.name, theme: appearanceToTheme[options.icon.appearance ?? "info"] }
				: {}),
		});
	});
}

function getCollectionKeys(block: any, type: BlockDataKey["comesFrom"] = "dataScript"): string[] {
	// traverse up the block to get list of dataKeys set
	const repeaterBlock = block.getRepeaterParent();
	const keys: string[] = [];
	if (repeaterBlock) {
		const collectionKey = repeaterBlock.getDataKey("key");
		const comesFrom = repeaterBlock.getDataKey("comesFrom");
		if (collectionKey && comesFrom == type) {
			keys.push(collectionKey);
		}
		const parentKeys: string[] = getCollectionKeys(repeaterBlock, type);
		if (parentKeys.length > 0) {
			keys.unshift(...parentKeys);
		}
	}
	return keys;
}

// Drill into data for blocks inside repeaters (uses the first item of each collection)
function getRepeaterScopedData(
	block: Block | null,
	data: Record<string, any>,
	type: BlockDataKey["comesFrom"] = "dataScript",
): Record<string, any> {
	let collectionObject = data || {};
	if (block?.isInsideRepeater()) {
		const keys = getCollectionKeys(block, type);
		collectionObject = keys.reduce((acc: any, key: string) => {
			const data = getDataForKey(acc, key);
			return Array.isArray(data) && data.length > 0 ? data[0] : data;
		}, collectionObject);
	}
	return collectionObject || {};
}

function triggerCopyEvent() {
	document.execCommand("copy");
}

type BlockPropsWithTraceback = Record<string, BlockProps[string] & { block?: Block }>;

const getParentProps = (
	baseBlock: Block,
	baseProps: BlockPropsWithTraceback = {},
): BlockPropsWithTraceback => {
	const parentBlock = baseBlock.getParentBlock();
	if (parentBlock) {
		const parentProps: BlockPropsWithTraceback = {};
		Object.entries(parentBlock.getBlockProps())
			.filter(([_, propDetails]) => {
				return propDetails.isPassedDown;
			})
			.forEach(([propName, propDetails]) => {
				parentProps[propName] = {
					...propDetails,
					block: parentBlock,
				};
			});
		const combinedProps = { ...parentProps, ...baseProps };
		return getParentProps(parentBlock, combinedProps);
	} else {
		return baseProps;
	}
};

const getDefaultPropsList = (block: Block): BlockProps => {
	const isCurrentBlockInRepeater = block?.isInsideRepeater();
	const repeaterRoot = isCurrentBlockInRepeater ? block?.getRepeaterParent() : null;
	if (repeaterRoot) {
		const key = repeaterRoot.getDataKey("key");
		const comesFrom = repeaterRoot.getDataKey("comesFrom");
		if (key && comesFrom === "props") {
			const propsRoot = repeaterRoot.getPropsRoot();
			if (!propsRoot) return {};
			const parsedValue = getStandardPropValue(key, propsRoot)?.value;
			if (!parsedValue) return {};
			if (Array.isArray(parsedValue)) {
				return {
					item: {
						value: parsedValue[0],
						isStandard: false,
						isDynamic: true,
						comesFrom: "props",
						isPassedDown: true,
					},
				};
			} else if (typeof parsedValue === "object") {
				return {
					key: {
						value: Object.keys(parsedValue)[0],
						isStandard: false,
						isDynamic: true,
						comesFrom: "props",
						isPassedDown: true,
					},
					value: {
						value: parsedValue[Object.keys(parsedValue)[0]],
						isStandard: false,
						isDynamic: true,
						comesFrom: "props",
						isPassedDown: true,
					},
				};
			}
		}
	}
	return {};
};

const PARSEABLE_STANDARD_TYPES = ["number", "boolean", "object", "array"];

// TODO: re-visit all props related functions as block props are now replaced with component props
const getPropValue = (
	propName: string,
	block: Block,
	getDataScriptValue: (path: string) => any = () => undefined,
	defaultProps?: BlockProps | null,
	getComponentScopedDataValue: (path: string) => any = () => undefined,
): any => {
	// Check default props first
	if (defaultProps?.[propName] !== undefined) {
		return defaultProps[propName].value;
	}

	let parentProps: BlockPropsWithTraceback | null = null;

	// Find matching prop from block or parent
	const blockProps = block.getBlockProps();
	let matchingProp: BlockPropsWithTraceback[string] =
		blockProps[propName] ?? (parentProps = getParentProps(block))[propName];

	if (!matchingProp) {
		return undefined;
	}

	// Handle dynamic props
	if (matchingProp.isDynamic) {
		if (matchingProp.comesFrom === "props" && matchingProp.value) {
			if (defaultProps?.[matchingProp.value] !== undefined) {
				return defaultProps[matchingProp.value].value;
			}
			if (parentProps === null) {
				parentProps = getParentProps(block);
			}
			const newMatchingProp = parentProps[matchingProp.value];
			if (!newMatchingProp?.block) return undefined;
			return getPropValue(
				matchingProp.value,
				newMatchingProp.block,
				getDataScriptValue,
				defaultProps,
				getComponentScopedDataValue,
			);
		}
		if (matchingProp.comesFrom === "dataScript" && matchingProp.value) {
			return getDataScriptValue(matchingProp.value);
		}
		if (matchingProp.comesFrom === "componentData" && matchingProp.value) {
			return getComponentScopedDataValue(matchingProp.value);
		}

		// Fallback to default props
		if (matchingProp.value && defaultProps?.[matchingProp.value] !== undefined) {
			return defaultProps[matchingProp.value].value;
		}

		return undefined;
	}

	// Handle standard props
	if (matchingProp.isStandard && matchingProp.propOptions) {
		const { type, options } = matchingProp.propOptions;
		const defaultValue = options?.defaultValue ?? null;

		if (PARSEABLE_STANDARD_TYPES.includes(type)) {
			if (matchingProp.value) {
				return JSON.parse(matchingProp.value);
			} else {
				if (typeof defaultValue === "string") {
					return JSON.parse(defaultValue);
				}
				return defaultValue;
			}
		}
		return matchingProp.value || defaultValue;
	}

	return matchingProp.value;
};

const getStandardPropValue = (
	propName: string,
	componentRoot: Block,
): { value: any; options: Record<string, any> } | undefined => {
	const propsOfComponentRoot = componentRoot.getBlockProps();
	if (propsOfComponentRoot) {
		for (const [name, value] of Object.entries(propsOfComponentRoot)) {
			if (propName === name && value.isStandard) {
				if (PARSEABLE_STANDARD_TYPES.includes(value.propOptions?.type || "string")) {
					const parsedValue = value.value
						? JSON.parse(value.value)
						: value.propOptions?.options?.defaultValue || null;
					return {
						value: parsedValue,
						options: value.propOptions?.options || {},
					};
				} else {
					return {
						value: value.value || value.propOptions?.options?.defaultValue || null,
						options: value.propOptions?.options || {},
					};
				}
			}
		}
		return undefined;
	} else {
		return undefined;
	}
};

const extractComponentId = (block: Block): string | null => {
	const { editingMode, fragmentData } = useCanvasStore();
	let componentId = block.extendedFromComponent || null;
	if (!componentId) {
		// in fragment mode the component root does not have extendedFromComponent
		if (editingMode == "fragment" && !block.getParentBlock()) componentId = fragmentData.fragmentId!;
	}
	return componentId;
};

const getDataArray = (collectionObject: Record<string, any>) => {
	const result: string[] = [];
	let collectionObjectCopy = { ...collectionObject };

	function processObject(obj: Record<string, any>, prefix = "") {
		Object.entries(obj).forEach(([key, value]) => {
			const path = prefix ? `${prefix}.${key}` : key;

			if (value === null) {
				result.push(path);
			} else if (typeof value === "object" && !Array.isArray(value)) {
				processObject(value, path);
			} else if (["string", "number", "boolean"].includes(typeof value)) {
				result.push(path);
			}
		});
	}

	processObject(collectionObjectCopy);
	return result;
};

function isDialogOpen() {
	return !!document.querySelector("[role='dialog']");
}

function parseJSONWithFallback<T>(value: T | string | undefined, fallback: T): T {
	if (value === undefined || value === null || value === "") {
		return fallback;
	}
	if (typeof value === "string") {
		try {
			return JSON.parse(value) as T;
		} catch {
			return fallback;
		}
	}
	return value as T;
}

export {
	addPxToNumber,
	alert,
	confirm,
	copyToClipboard,
	cssUrl,
	dataURLtoFile,
	detachBlockFromComponent,
	extractNumberAndUnit,
	findNearestSiblingIndex,
	generateId,
	getBlock,
	getBlockCopy,
	getBlockInfo,
	getBlockInstance,
	getBlockObjectCopy as getBlockObject,
	getBlockString,
	getBoxSpacing,
	getCopyWithoutParent,
	getDataArray,
	getDataForKey,
	getDefaultPropsList,
	getImageBlock,
	getNumberFromPx,
	getParentProps,
	getPropValue,
	getRepeaterScopedData,
	getRGB,
	getRootBlockTemplate,
	getRouteVariables,
	getStandardPropValue,
	extractComponentId,
	getTextContent,
	getVideoBlock,
	handleBase64Attribute,
	HexToHSV,
	HSVToHex,
	isBlock,
	isCtrlOrCmd,
	isDialogOpen,
	isHTMLString,
	isInteractiveControl,
	isJSONString,
	isTargetEditable,
	kebabToCamelCase,
	mapToObject,
	normalizeCSSPropertyName,
	normalizeValueWithUnits,
	openInDesk,
	parseAndSetBackground,
	removeDefaultUnit,
	replaceMapKey,
	setBoxSpacing,
	shortenNumber,
	showDialog,
	stripStatePrefix,
	toCSSProperty,
	toKebabCase,
	toStyleProperty,
	toTitleCase,
	triggerCopyEvent,
	uploadBuilderAsset,
	uploadUserFont,
	parseJSONWithFallback,
	deepEqual,
	diffArray,
};
