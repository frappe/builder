import AlertDialog from "@/components/AlertDialog.vue";
import { confirmDialog, FileUploadHandler } from "frappe-ui";
import { h, reactive, toRaw } from "vue";
import { toast } from "vue-sonner";
import Block from "./block";

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
	const [r, g, b] = color
		.replace("#", "")
		.match(/.{1,2}/g)
		?.map((x) => parseInt(x, 16)) || [0, 0, 0];

	const max = Math.max(r, g, b);
	const min = Math.min(r, g, b);
	const v = max / 255;
	const d = max - min;
	const s = max === 0 ? 0 : d / max;
	const h =
		max === min
			? 0
			: max === r
			? (g - b) / d + (g < b ? 6 : 0)
			: max === g
			? (b - r) / d + 2
			: (r - g) / d + 4;
	return { h: h * 60, s, v };
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
			onClick: resolve,
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
	return key.split(".").reduce((d, key) => (d ? d[key] : null), data) as string;
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

function logObjectDiff(obj1: { [key: string]: {} }, obj2: { [key: string]: {} }, path = []) {
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

async function uploadImage(file: File, silent = false) {
	const uploader = new FileUploadHandler();
	let fileDoc = {
		file_url: "",
		file_name: "",
	};
	const upload = uploader.upload(file, {
		private: false,
		folder: "Home/Builder Uploads",
		optimize: true,
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
			const init = new Promise((done) => (window.Module = { onRuntimeInitialized: done }));
			await loadScript(path).then(() => init);
		}
		return Uint8Array.from(Module.decompress(arrayBuffer)).buffer;
	}
	return arrayBuffer;
}

async function getFontName(file_url: string) {
	const opentype = await import("opentype.js");
	return opentype.parse(await getFontArrayBuffer(file_url)).names.fullName.en;
}

function generateId() {
	return Math.random().toString(36).substr(2, 9);
}

export {
	addPxToNumber,
	alert,
	confirm,
	copyToClipboard,
	dataURLtoFile,
	detachBlockFromComponent,
	findNearestSiblingIndex,
	generateId,
	getBlockCopy,
	getBlockInstance,
	getBlockObjectCopy as getBlockObject,
	getBlockString,
	getCopyWithoutParent,
	getDataForKey,
	getFontName,
	getNumberFromPx,
	getRandomColor,
	getRGB,
	getRouteVariables,
	getTextContent,
	HexToHSV,
	HSVToHex,
	isCtrlOrCmd,
	isHTMLString,
	isJSONString,
	isTargetEditable,
	kebabToCamelCase,
	logObjectDiff,
	mapToObject,
	replaceMapKey,
	RGBToHex,
	stripExtension,
	uploadImage,
};
