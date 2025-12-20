import Block from "@/block";
import AlertDialog from "@/components/AlertDialog.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import getBlockTemplate from "@/utils/blockTemplate";
import { confirmDialog, FileUploadHandler } from "frappe-ui";
import { defineComponent, h, markRaw, reactive, ref, toRaw } from "vue";
import { toast } from "vue-sonner";
import Dialog from "../components/Controls/Dialog.vue";
import { builderSettings } from "@/data/builderSettings";

function getNumberFromPx(px: string | number | null | undefined): number {
	if (!px) {
		return 0;
	}
	if (typeof px === "number") {
		return px;
	}
	const number = Number(px.replace("px", ""));
	if (isNaN(number)) {
		return 0;
	}
	return number;
}

function addPxToNumber(number: number, round: boolean = true): string {
	number = round ? Math.round(number) : number;
	return `${number}px`;
}

function HexToHSV(color: HashString): { h: number; s: number; v: number } {
	// Remove hash and normalize length
	let hex = color.replace("#", "").trim();

	// Expand short hex (#abc -> #aabbcc)
	if (hex.length === 3) {
		hex = hex
			.split("")
			.map((c) => c + c)
			.join("");
	}

	// If not valid hex, return black
	if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
		return { h: 0, s: 0, v: 0 };
	}

	const r = parseInt(hex.slice(0, 2), 16);
	const g = parseInt(hex.slice(2, 4), 16);
	const b = parseInt(hex.slice(4, 6), 16);

	const max = Math.max(r, g, b);
	const min = Math.min(r, g, b);
	const v = max / 255;
	const d = max - min;
	const s = max === 0 ? 0 : d / max;

	let h = 0;
	if (d !== 0) {
		if (max === r) {
			h = (g - b) / d + (g < b ? 6 : 0);
		} else if (max === g) {
			h = (b - r) / d + 2;
		} else {
			h = (r - g) / d + 4;
		}
		h *= 60;
	}

	return { h, s, v };
}

function HSVToHex(h: number, s: number, v: number): HashString {
	s /= 100;
	v /= 100;
	h /= 360;

	let r = 0,
		g = 0,
		b = 0;

	let i = Math.floor(h * 6);
	let f = h * 6 - i;
	let p = v * (1 - s);
	let q = v * (1 - f * s);
	let t = v * (1 - (1 - f) * s);

	switch (i % 6) {
		case 0:
			(r = v), (g = t), (b = p);
			break;
		case 1:
			(r = q), (g = v), (b = p);
			break;
		case 2:
			(r = p), (g = v), (b = t);
			break;
		case 3:
			(r = p), (g = q), (b = v);
			break;
		case 4:
			(r = t), (g = p), (b = v);
			break;
		case 5:
			(r = v), (g = p), (b = q);
			break;
	}
	r = Math.round(r * 255);
	g = Math.round(g * 255);
	b = Math.round(b * 255);
	return `#${[r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

function getRandomColor() {
	return HSVToHex(Math.random() * 360, 25, 100);
}

async function confirm(message: string, title: string = "Confirm"): Promise<boolean> {
	return new Promise((resolve) => {
		confirmDialog({
			title: title,
			message: message,
			onConfirm: ({ hideDialog }: { hideDialog: Function }) => {
				resolve(true);
				hideDialog();
			},
			onCancel: () => {
				resolve(false);
			},
		});
	});
}

async function alert(message: string, title: string = "Alert"): Promise<boolean> {
	return new Promise((resolve) => {
		h(AlertDialog, {
			title,
			message,
			onClick: () => resolve(true),
		});
	});
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

function RGBToHex(rgb: RGBString): HashString {
	const [r, g, b] = rgb
		.replace("rgb(", "")
		.replace(")", "")
		.split(",")
		.map((x) => parseInt(x));
	return `#${[r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

function getRGB(color: HashString | RGBString | string | null): HashString | null {
	if (!color) {
		return null;
	}
	if (color.startsWith("rgb")) {
		return RGBToHex(color as RGBString);
	} else if (!color.startsWith("#") && color.match(/\b[a-fA-F0-9]{3,6}\b/g)) {
		return `#${color}` as HashString;
	}
	return color as HashString;
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

function stripExtension(string: string) {
	const lastDotPosition = string.lastIndexOf(".");
	if (lastDotPosition === -1) {
		return string;
	}
	return string.substr(0, lastDotPosition);
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

function logObjectDiff(obj1: Record<string, any>, obj2: Record<string, any>, path: string[] = []) {
	if (!obj1 || !obj2) return;
	for (const key in obj1) {
		const newPath = path.concat(key);

		if (obj2.hasOwnProperty(key)) {
			if (typeof obj1[key] === "object" && typeof obj2[key] === "object") {
				logObjectDiff(obj1[key], obj2[key], newPath);
			} else {
				if (obj1[key] !== obj2[key]) {
					console.log(`Difference at ${newPath.join(".")} - ${obj1[key]} !== ${obj2[key]}`);
				}
			}
		} else {
			// console.log(`Property ${newPath.join(".")} is missing in the second object`);
		}
	}

	for (const key in obj2) {
		if (!obj1.hasOwnProperty(key)) {
			// console.log(`Property ${key} is missing in the first object`);
		}
	}
}

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
	blockCopy.rawStyles = component?.rawStyles
		? { ...component.rawStyles, ...block.rawStyles }
		: block.rawStyles;
	blockCopy.isRepeaterBlock = component?.isRepeaterBlock || block.isRepeaterBlock;
	blockCopy.visibilityCondition = component?.visibilityCondition || block.visibilityCondition;
	blockCopy.innerHTML = block.innerHTML || component?.innerHTML;
	delete blockCopy.extendedFromComponent;
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
	delete blockCopy.ownBlockData;
	delete blockCopy.passedDownBlockData;
	return blockCopy;
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
		let arr = dataurl.split(","),
			mime = arr[0].match(/:(.*?);/)?.[1],
			bstr = atob(arr[1]),
			n = bstr.length,
			u8arr = new Uint8Array(n);
		while (n--) {
			u8arr[n] = bstr.charCodeAt(n);
		}
		return new File([u8arr], filename, { type: mime });
	} catch (error) {
		console.error(`Failed to convert dataURL ${dataurl} to file.`);
		return null;
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

async function getFontArrayBuffer(file_url: string) {
	const arrayBuffer = await fetch(file_url).then((res) => res.arrayBuffer());
	if (file_url.endsWith(".woff2")) {
		const loadScript = (src: string) =>
			new Promise((onload) =>
				document.documentElement.append(Object.assign(document.createElement("script"), { src, onload })),
			);
		if (!window.Module) {
			const path = "https://unpkg.com/wawoff2@2.0.1/build/decompress_binding.js";
			// @ts-ignore
			const init = new Promise((done) => (window.Module = { onRuntimeInitialized: done }));
			await loadScript(path).then(() => init);
		}
		return Uint8Array.from(window.Module.decompress(arrayBuffer)).buffer;
	}
	return arrayBuffer;
}

async function getFontName(file_url: string) {
	const opentype = await import("opentype.js");
	return opentype.parse(await getFontArrayBuffer(file_url)).names.fullName.en;
}

async function getFontNameFromFile(file: File): Promise<string> {
	const arrayBuffer = await file.arrayBuffer();
	let buffer = arrayBuffer;
	if (file.name.endsWith(".woff2")) {
		const loadScript = (src: string) =>
			new Promise((onload) =>
				document.documentElement.append(Object.assign(document.createElement("script"), { src, onload })),
			);
		if (!window.Module) {
			const path = "https://unpkg.com/wawoff2@2.0.1/build/decompress_binding.js";
			// @ts-ignore
			const init = new Promise((done) => (window.Module = { onRuntimeInitialized: done }));
			await loadScript(path).then(() => init);
		}
		buffer = Uint8Array.from(window.Module.decompress(arrayBuffer)).buffer;
	}
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
	return Math.random().toString(36).substr(2, 9);
}

function throttle<T extends (...args: any[]) => void>(func: T, wait: number = 1000) {
	let timeout: ReturnType<typeof setTimeout> | null = null;
	let lastArgs: Parameters<T> | null = null;
	let pending = false;

	const invoke = (...args: Parameters<T>) => {
		lastArgs = args;
		if (timeout) {
			pending = true;
			return;
		}

		func(...lastArgs);
		timeout = setTimeout(() => {
			timeout = null;
			if (pending && lastArgs) {
				pending = false;
				invoke(...lastArgs);
			}
		}, wait);
	};

	return invoke;
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

interface BackgroundValue {
	image?: string;
	position?: string;
	size?: string;
	repeat?: string;
	attachment?: string;
	origin?: string;
	clip?: string;
	color?: string;
}

// Based on WebKit and Gecko parsing implementations
function parseBackground(cssText: string): BackgroundValue {
	if (!cssText || typeof cssText !== "string") {
		return {};
	}

	// Tokenize the input preserving quoted strings and functions
	function tokenize(input: string): string[] {
		const tokens: string[] = [];
		let current = "";
		let parenDepth = 0;
		let inQuote: string | null = null;

		for (let i = 0; i < input.length; i++) {
			const char = input[i];

			if (inQuote) {
				current += char;
				if (char === inQuote && input[i - 1] !== "\\") {
					inQuote = null;
				}
				continue;
			}

			if (char === '"' || char === "'") {
				current += char;
				inQuote = char;
				continue;
			}

			if (char === "(") {
				parenDepth++;
				current += char;
				continue;
			}

			if (char === ")") {
				parenDepth--;
				current += char;
				continue;
			}

			if (parenDepth > 0) {
				current += char;
				continue;
			}

			if (char === " " || char === "\t" || char === "\n") {
				if (current) {
					tokens.push(current);
					current = "";
				}
				continue;
			}

			current += char;
		}

		if (current) {
			tokens.push(current);
		}

		return tokens;
	}

	// Parse color value
	function isColor(value: string): boolean {
		return (
			/^(#|rgb|hsl|[a-z]+$)/.test(value) &&
			!["center", "top", "bottom", "left", "right", "fixed", "local", "scroll", "contain", "repeat"].includes(
				value,
			)
		);
	}

	// Parse position values
	function isPosition(value: string): boolean {
		return /^(center|top|bottom|left|right|[-\d.]+(%|px|em|rem|vh|vw)?)$/.test(value);
	}

	// Parse size values
	function isSize(value: string): boolean {
		return /^(cover|contain|auto|[-\d.]+(%|px|em|rem|vh|vw)?)$/.test(value);
	}

	const result: BackgroundValue = {};
	const tokens = tokenize(cssText.trim());
	let i = 0;

	while (i < tokens.length) {
		const token = tokens[i];

		// Handle url() and gradients
		if (token.startsWith("url(") || token.includes("gradient")) {
			result.image = token;
			i++;
			continue;
		}

		// Handle color
		if (isColor(token)) {
			result.color = token;
			i++;
			continue;
		}

		// Handle position and size
		if (isPosition(token)) {
			let position = [token];

			// Check for second position value
			if (i + 1 < tokens.length && isPosition(tokens[i + 1])) {
				position.push(tokens[i + 1]);
				i++;
			}

			result.position = position.join(" ");

			// Check for size after '/'
			if (i + 2 < tokens.length && tokens[i + 1] === "/" && isSize(tokens[i + 2])) {
				let size = [tokens[i + 2]];
				if (i + 3 < tokens.length && isSize(tokens[i + 3])) {
					size.push(tokens[i + 3]);
					i++;
				}
				result.size = size.join(" ");
				i += 2;
			}

			i++;
			continue;
		}

		// Handle repeat
		if (/^(no-repeat|repeat(-[xy])?|round|space)$/.test(token)) {
			result.repeat = token;
			i++;
			continue;
		}

		// Handle attachment
		if (/^(fixed|local|scroll)$/.test(token)) {
			result.attachment = token;
			i++;
			continue;
		}

		// Handle origin/clip
		if (/^(border|padding|content)-box$/.test(token)) {
			if (!result.origin) {
				result.origin = token;
			} else {
				result.clip = token;
			}
			i++;
			continue;
		}

		i++;
	}

	return result;
}

const parseAndSetBackground = (styles: BlockStyleMap) => {
	if (styles.background) {
		const { color, image, position, size, repeat } = parseBackground(styles.background as string);
		delete styles.background;
		if (color) styles.backgroundColor = color;
		if (image) styles.backgroundImage = image;
		if (position) styles.backgroundPosition = position;
		if (size) styles.backgroundSize = size;
		if (repeat) styles.backgroundRepeat = repeat;
	}
};

function shortenNumber(num: number): string {
	if (num < 1000) return num.toString();
	const units = ["", "k", "M", "B", "T"];
	const order = Math.floor(Math.log10(num) / 3);
	const unitname = units[order];
	const shortNum = num / Math.pow(1000, order);
	return shortNum % 1 === 0 ? shortNum.toFixed(0) + unitname : shortNum.toFixed(1) + unitname;
}

function setBoxSpacing(block: Block, type: "padding" | "margin", value: string) {
	const props = [type, `${type}Top`, `${type}Right`, `${type}Bottom`, `${type}Left`];
	props.forEach((prop) => block.setStyle(prop, null));
	if (!value) return;
	const arr = value.split(" ");
	if (arr.length === 1) {
		block.setStyle(type, arr[0]);
	} else if (arr.length === 2) {
		block.setStyle(`${type}Top`, arr[0]);
		block.setStyle(`${type}Bottom`, arr[0]);
		block.setStyle(`${type}Left`, arr[1]);
		block.setStyle(`${type}Right`, arr[1]);
	} else if (arr.length === 3) {
		block.setStyle(`${type}Top`, arr[0]);
		block.setStyle(`${type}Left`, arr[1]);
		block.setStyle(`${type}Right`, arr[1]);
		block.setStyle(`${type}Bottom`, arr[2]);
	} else if (arr.length === 4) {
		block.setStyle(`${type}Top`, arr[0]);
		block.setStyle(`${type}Right`, arr[1]);
		block.setStyle(`${type}Bottom`, arr[2]);
		block.setStyle(`${type}Left`, arr[3]);
	}
}

function getBoxSpacing(
	block: Block,
	type: "padding" | "margin",
	opts?: { nativeOnly?: boolean; cascading?: boolean },
): string {
	const nativeOnly = opts?.nativeOnly ?? false;
	const cascading = opts?.cascading ?? false;
	const base = String(block.getStyle(type, undefined, nativeOnly, cascading) ?? "0px");
	const top = block.getStyle(`${type}Top`, undefined, nativeOnly, cascading) ?? base;
	const bottom = block.getStyle(`${type}Bottom`, undefined, nativeOnly, cascading) ?? base;
	const left = block.getStyle(`${type}Left`, undefined, nativeOnly, cascading) ?? base;
	const right = block.getStyle(`${type}Right`, undefined, nativeOnly, cascading) ?? base;
	const sTop = String(top);
	const sBottom = String(bottom);
	const sLeft = String(left);
	const sRight = String(right);
	if (sTop === base && sBottom === base && sLeft === base && sRight === base) return base;
	if (sTop === sBottom && sTop === sRight && sTop === sLeft) return sTop;
	if (sTop === sBottom && sLeft === sRight) return `${sTop} ${sLeft}`;
	return `${sTop} ${sRight} ${sBottom} ${sLeft}`;
}

/**
 * Extracts the numeric value and unit from a CSS value string
 * @param value - CSS value string (e.g., "10px", "1.5em", "20")
 * @returns Object containing the number and unit parts
 */
function extractNumberAndUnit(value: string): { number: string; unit: string } {
	const match = value.match(/([0-9.]+)([a-z%]*)/) || ["", "0", ""];
	return { number: match[1], unit: match[2] };
}

/**
 * Adds a unit to a number if it doesn't already have one
 * @param numberStr - String containing a number with or without a unit
 * @param unit - Default unit to add if none exists
 * @returns String with unit attached
 */
function addUnitToNumber(numberStr: string, unit: string): string {
	const match = numberStr.match(/^([0-9.]+)([a-z%]*)$/);
	if (match) {
		const [, number, existingUnit] = match;
		return existingUnit ? numberStr : number + unit;
	}
	return numberStr;
}

/**
 * Normalizes CSS values by adding default units where missing
 * Handles both single values and spacing properties with multiple values
 * @param value - CSS value string
 * @param unitOptions - Array of possible units, first is used as default
 * @param styleProperty - CSS property name (used to detect spacing properties)
 * @returns Normalized value string with units added
 */
function normalizeValueWithUnits(value: string, unitOptions: string[], styleProperty: string): string {
	if (!unitOptions.length) return value;

	const defaultUnit = unitOptions[0];
	const isSpacingProperty = styleProperty === "margin" || styleProperty === "padding";

	if (isSpacingProperty) {
		const parts = value.trim().split(/\s+/);
		if (parts.length > 1) {
			return parts.map((part) => addUnitToNumber(part, defaultUnit)).join(" ");
		}
	}

	return addUnitToNumber(value, defaultUnit);
}

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
	return new Promise((resolve) => {
		const isOpen = ref(true);
		const dialogOptions = {
			title: options.title || "",
			message: options.message,
			icon: options.icon,
			size: options.size || "md",
			actions: (options.actions || []).map((action) => ({
				label: action.label,
				variant: action.variant || "subtle",
				theme: action.theme || "gray",
				onClick: async ({ close }: { close: () => void }) => {
					if (action.onClick) {
						await action.onClick();
					}
					close();
				},
			})),
		};

		const DialogComponent = markRaw(
			defineComponent({
				name: "DynamicDialog",
				setup() {
					const handleClose = () => {
						isOpen.value = false;
						// Remove dialog from appDialogs after animation
						setTimeout(() => {
							const builderStore = useBuilderStore();
							const index = builderStore.appDialogs.indexOf(DialogComponent);
							if (index > -1) {
								builderStore.appDialogs.splice(index, 1);
							}
							resolve();
						}, 200);
					};

					return () =>
						h(Dialog, {
							modelValue: isOpen.value,
							"onUpdate:modelValue": (val: boolean) => {
								isOpen.value = val;
								if (!val) handleClose();
							},
							options: dialogOptions,
						});
				},
			}),
		) as typeof Dialog;

		const builderStore = useBuilderStore();
		builderStore.appDialogs.push(DialogComponent);
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

function triggerCopyEvent() {
	document.execCommand("copy");
}

const getValueForInheritedProp = (
	propName: string,
	block: Block,
	getDataScriptValue: (path: string) => any,
): any => {
	let parent = block.getParentBlock();
	while (parent) {
		const parentProps = parent.getBlockProps();
		const matchingProp = parentProps[propName];
		if (matchingProp) {
			if (matchingProp.isDynamic) {
				if (matchingProp.comesFrom === "dataScript" && matchingProp.value) {
					return getDataScriptValue(matchingProp.value);
				} else if (matchingProp.comesFrom === "blockDataScript" && matchingProp.value) {
					return block.getBlockData("passedDown")[matchingProp.value];
				} else {
					return getValueForInheritedProp(propName, parent, getDataScriptValue);
				}
			} else {
				if (matchingProp.isStandard && matchingProp.standardOptions) {
					if (
						matchingProp.standardOptions.type !== "string" &&
						matchingProp.standardOptions.type !== "select"
					) {
						return matchingProp.value
							? JSON.parse(matchingProp.value)
							: matchingProp.standardOptions?.options?.defaultValue || null;
					} else {
						return matchingProp.value || matchingProp.standardOptions?.options?.defaultValue || null;
					}
				}
				return matchingProp.value;
			}
		}
		parent = parent.getParentBlock();
	}
	return undefined;
};

const getPropValue = (
	propName: string,
	block: Block,
	getDataScriptValue: (path: string) => any,
	defaultProps?: Record<string, any> | null,
): any => {
	if (defaultProps && defaultProps[propName] !== undefined) {
		return defaultProps[propName].value;
	}
	const blockProps = block.getBlockProps();
	if (blockProps[propName]) {
		const prop = blockProps[propName];
		if (prop.isDynamic) {
			if (prop.comesFrom === "dataScript" && prop.value) {
				return getDataScriptValue(prop.value);
			} else if (prop.comesFrom === "blockDataScript" && prop.value) {
				return block.getBlockData("passedDown")[prop.value];
			} else {
				if (prop.value && defaultProps && defaultProps[prop.value] !== undefined) {
					return defaultProps[prop.value].value;
				}
				if (prop.value) {
					return getValueForInheritedProp(prop.value, block, getDataScriptValue);
				}
			}
		} else {
			if (prop.isStandard && prop.standardOptions) {
				if (prop.standardOptions.type !== "string" && prop.standardOptions.type !== "select") {
					return prop.value ? JSON.parse(prop.value) : prop.standardOptions?.options?.defaultValue || null;
				} else {
					return prop.value || prop.standardOptions?.options?.defaultValue || null;
				}
			}
			return prop.value;
		}
	}
	return undefined;
};

const getStandardPropValue = (
	propName: string,
	componentRoot: Block,
): { value: any; options: Record<string, any> } | undefined => {
	const propsOfComponentRoot = componentRoot.getBlockProps();
	if (propsOfComponentRoot) {
		for (const [name, value] of Object.entries(propsOfComponentRoot)) {
			if (propName === name && value.isStandard) {
				if (value.standardOptions?.type !== "string" && value.standardOptions?.type !== "select") {
					const parsedValue = value.value
						? JSON.parse(value.value)
						: value.standardOptions?.options?.defaultValue || null;
					return {
						value: parsedValue,
						options: value.standardOptions?.options || {},
					};
				} else {
					return {
						value: value.value || value.standardOptions?.options?.defaultValue || null,
						options: value.standardOptions?.options || {},
					};
				}
			}
		}
		return undefined;
	} else {
		return undefined;
	}
};

const getDataArray = (
	block: Block,
	collectionObject: Record<string, any>,
	comesFrom: BlockDataKey["comesFrom"],
) => {
	const result: string[] = [];
	let collectionObjectCopy = { ...collectionObject };
	if (block.isInsideRepeater() && comesFrom == "dataScript") {
		const keys = getCollectionKeys(block, comesFrom);
		collectionObjectCopy = keys.reduce((acc: any, key: string) => {
			const data = getDataForKey(acc, key);
			return Array.isArray(data) && data.length > 0 ? data[0] : data;
		}, collectionObjectCopy);
	}

	function processObject(obj: Record<string, any>, prefix = "") {
		Object.entries(obj).forEach(([key, value]) => {
			const path = prefix ? `${prefix}.${key}` : key;

			if (typeof value === "object" && value !== null && !Array.isArray(value)) {
				processObject(value, path);
			} else if (["string", "number", "boolean"].includes(typeof value)) {
				result.push(path);
			}
		});
	}

	processObject(collectionObjectCopy);
	return result;
};

/**
 * Tries to execute user-provided script in a safer environment, (but not guarantee) restricting access to certain DOM properties and methods.
 * It makes the editor canvas as the root (document), and thus limits the script's ability to manipulate the broader document.
 * It tries to restrict escape hatches which could be used to access the global window or document objects.
 * It tries to `wrap` all returned DOM nodes and collections to ensure they are also proxied.
 * The `wrap` function creates proxies for DOM elements to intercept property access and method calls.
 *
 * @param blockId - The ID of the block element to which the script is associated.
 * @param userScript - The user-provided JavaScript code to execute.
 * @param props - An optional object containing properties to be made available in the script's context.
 */

function saferExecuteBlockClientScript(
	blockUid: string,
	userScript: string,
	props: Record<string, any> = {},
) {
	const cache = new WeakMap();

	const BLOCKED_GET = new Set([
		"ownerDocument",
		"document",
		"defaultView",
		"window",
		"globalThis",
		"parentElement",
		"parentNode",
		"innerHTML",
		"outerHTML",
	]);

	const BLOCKED_SET = new Set(["innerHTML", "outerHTML"]);

	function wrap(value: Element | Node) {
		if (value === null || typeof value !== "object") return value;
		if (cache.has(value)) return cache.get(value);

		const proxy = new Proxy(value, handler);
		cache.set(value, proxy);
		return proxy;
	}

	const handler = {
		get(target: Element, prop: string, receiver: any) {
			if (BLOCKED_GET.has(prop)) return undefined;

			let val = Reflect.get(target, prop, receiver);

			// Wrap DOM returns
			if (val instanceof Node) return wrap(val);
			if (val instanceof NamedNodeMap || val instanceof DOMTokenList || val instanceof CSSStyleDeclaration)
				return wrap(val as any);

			if (val instanceof NodeList || val instanceof HTMLCollection) {
				return Array.from(val, wrap);
			}

			// Wrap functions (methods)
			if (typeof val === "function") {
				// disallow eventListeners
				if (prop === "addEventListener" || prop === "removeEventListener") {
					// disallow clicks
					return (...args: any[]) => {
						const eventType = args[0];
						const disallowClicks = Boolean(builderSettings.doc?.block_click_handlers);
						if (disallowClicks && (eventType === "click" || eventType === "dblclick")) {
							throw new Error(`Blocked: cannot add/remove ${eventType} event listeners`);
						}
						const realArgs = args.map((a) => cache.get(a) || a);
						return val.apply(target, realArgs);
					};
				}
				return (...args) => {
					const realArgs = args.map((a) => cache.get(a) || a);

					// Do not allow inserting nodes outside the sandbox
					for (const a of realArgs) {
						if (a instanceof Node && !sandboxRoot.contains(a)) {
							throw new Error("Blocked: external node insertion");
						}
					}

					const result = val.apply(target, realArgs);
					return wrap(result);
				};
			}

			return val; // primitive allowed
		},

		set(target: Element, prop: string, value: any) {
			if (BLOCKED_SET.has(prop)) {
				throw new Error(`Blocked: cannot set ${prop}`);
			}

			// Allow normal DOM props like src, value, className, id, etc.
			try {
				return Reflect.set(target as any, prop as any, value);
			} catch {
				return false;
			}
		},
	};

	const sandboxRoot = document.querySelector("[data-block-id='root']") as HTMLElement;
	const thisElement = document.querySelector(`[data-block-uid='${blockUid}']`) as HTMLElement;

	const proxiedRoot = wrap(sandboxRoot);
	const proxiedThis = wrap(thisElement);

	const context = {
		document: proxiedRoot,
		thisRef: proxiedThis,
		props,
		// Escape hatches blocked
		window: undefined,
		globalThis: undefined,
		eval: undefined,
		Function: undefined,
		setTimeout: undefined,
		setInterval: undefined,
	};

	const fn = new Function(
		"context",
		`with (context) {
			return (function() { ${userScript} }).call(thisRef);
		}`,
	);

	try {
		fn.call(proxiedThis, context);
	} catch (e) {
		console.error("Error in user script:", e);
		// toast.warning("An error occurred while executing block script: " + (e instanceof Error ? e.message : ""));
	}
}

export {
	addPxToNumber,
	addUnitToNumber,
	alert,
	confirm,
	copyToClipboard,
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
	getCollectionKeys,
	getCopyWithoutParent,
	getDataForKey,
	getFontName,
	getImageBlock,
	getNumberFromPx,
	getRandomColor,
	getRGB,
	getRootBlockTemplate,
	getRouteVariables,
	getTextContent,
	getVideoBlock,
	HexToHSV,
	HSVToHex,
	isBlock,
	isCtrlOrCmd,
	isHTMLString,
	isJSONString,
	isTargetEditable,
	kebabToCamelCase,
	logObjectDiff,
	mapToObject,
	normalizeValueWithUnits,
	openInDesk,
	parseAndSetBackground,
	parseBackground,
	replaceMapKey,
	RGBToHex,
	setBoxSpacing,
	shortenNumber,
	showDialog,
	stripExtension,
	throttle,
	toKebabCase,
	triggerCopyEvent,
	uploadBuilderAsset,
	uploadUserFont,
	getPropValue,
	getStandardPropValue,
	getDataArray,
	saferExecuteBlockClientScript,
};
