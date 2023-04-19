import { BlockOptions, Styles } from "./block";
import Block from "./block";
function convertHtmlToBlocks(html: string) {
	const start = html.indexOf("```");
	let htmlStripped;
	if (start === -1) {
		htmlStripped = html;
	} else {
		const end = html.lastIndexOf("```");
		htmlStripped = html.substring(start + 3, end);
	}


	const doc = new DOMParser().parseFromString(htmlStripped, "text/html");
	const { body } = doc;
	return parseElement(body);
}

function parseElement(element: HTMLElement): BlockOptions {
	const obj: BlockOptions = {
		element: element.tagName.toLowerCase(),
		styles: {},
		attributes: {}
	};

	if (element.style.length) {
		for (let i = 0; i < element.style.length; i++) {
			const prop = element.style[i];
			obj.styles[prop] = element.style.getPropertyValue(prop);
		}
	}

	if (element.attributes.length) {
		for (let i = 0; i < element.attributes.length; i++) {
			const attr = element.attributes[i];
			obj.attributes[attr.name] = attr.value;
		}
	}

	// classes
	if (element.classList.length) {
		obj.classes = [];
		for (let i = 0; i < element.classList.length; i++) {
			obj.classes.push(element.classList[i]);
		}
	}

	if (element.hasChildNodes()) {
		obj.children = [];
		const { childNodes } = element;
		for (let i = 0; i < childNodes.length; i++) {
			const child = childNodes[i];
			console.log(child);
			if (child.nodeType === Node.ELEMENT_NODE) {
				obj.children.push(parseElement(child));
			} else if (child.nodeType === Node.TEXT_NODE) {
				obj.innerText = (child.textContent || '').trim();
			}
		}
	}

	return obj;
}

window.convertHtmlToBlocks = convertHtmlToBlocks;

declare global {
	interface Window {
		convertHtmlToBlocks: any;
	}
}


export default convertHtmlToBlocks;