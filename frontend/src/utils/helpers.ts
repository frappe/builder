import { confirmDialog } from "frappe-ui";
import { reactive, toRaw } from "vue";
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

function isCtrlOrCmd(e: KeyboardEvent) {
	return e.ctrlKey || e.metaKey;
}

const detachBlockFromComponent = (block: Block) => {
	const blockCopy = getBlockCopy(block);
	const component = block.getComponent();
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
	blockCopy.children = blockCopy.children.map(detachBlockFromComponent);
	return blockCopy;
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
	return blockCopy;
}

export {
	addPxToNumber,
	confirm,
	copyToClipboard,
	detachBlockFromComponent,
	findNearestSiblingIndex,
	getBlockCopy,
	getBlockInstance,
	getBlockObjectCopy as getBlockObject,
	getBlockString,
	getCopyWithoutParent,
	getDataForKey,
	getNumberFromPx,
	getRandomColor,
	getRGB,
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
};
