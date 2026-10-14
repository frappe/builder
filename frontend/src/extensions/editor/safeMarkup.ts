/**
 * DOMPurify checks markup before Builder adds it to the canvas.
 * This prevents extension markup from running outside its sandbox.
 */

import DOMPurify, { type RemovedAttribute, type RemovedElement } from "dompurify";
import { anyText, refuse, text } from "../bridge/params";

// a separate instance, so the hook in `ai/markdown.ts` does not apply here
const purifier = DOMPurify(window);
// DOMPurify removes `target` by default, but a link on a page often needs it
purifier.setConfig({ ADD_ATTR: ["target"] });

/** A tag name, with no markup in it. */
const ELEMENT_NAME = /^[a-z][a-z0-9-]*$/;

/** DOMPurify gives back an empty string when it removes the element itself. */
export const readElement = (value: unknown, field: string) => {
	const element = text(value, field);
	if (!ELEMENT_NAME.test(element)) throw refuse(`"${element}" is not an element name.`, "invalid_params");
	if (!purifier.sanitize(document.createElement(element))) {
		throw refuse(`An extension cannot add a <${element}> element.`, "invalid_params");
	}
	return element;
};

/** `null` removes an attribute, as `removeAttribute` does. */
export const readAttributes = (value: unknown, element: string, field: string) => {
	if (value === undefined) return undefined;
	if (typeof value !== "object" || value === null || Array.isArray(value)) {
		throw refuse(`"${field}" must be an object.`, "invalid_params");
	}
	return Object.fromEntries(
		Object.entries(value).map(([name, sent]) => [name, readAttribute(element, name, sent, field)]),
	);
};

export const isSafeAttribute = (element: string, name: string, value: string) =>
	purifier.isValidAttribute(element, name, value);

const readAttribute = (element: string, name: string, value: unknown, field: string) => {
	if (value === null) return undefined;
	const checked = anyText(value, `${field}.${name}`);
	if (!isSafeAttribute(element, name, checked)) {
		throw refuse(`<${element}> cannot have the attribute "${name}" with this value.`, "invalid_params");
	}
	return checked;
};

/**
 * A bound attribute can have any name, such as `darkSrc`, so only the names that
 * run code are refused. An attribute DOMPurify knows, such as `href`, needs a safe value.
 */
export const isSafeBoundAttribute = (element: string, name: string, value: string) =>
	!/^on|^srcdoc$/i.test(name) && (isSafeAttribute(element, name, value) || !isSafeAttribute(element, name, ""));

export const sanitizeHTML = (html: string) => {
	// a string that starts with <script> puts it in <head>, where DOMPurify neither
	// checks nor reports it. A template parses as `v-html` does, and loads nothing
	const template = document.createElement("template");
	template.innerHTML = html;
	return purifier.sanitize(template.content);
};

export const readHTML = (value: unknown, field: string) => {
	if (value === undefined) return undefined;
	const clean = sanitizeHTML(anyText(value, field));
	const [removed] = purifier.removed;
	if (removed) {
		throw refuse(`"${field}" holds markup that is not allowed: ${describe(removed)}.`, "invalid_params");
	}
	// a browser can parse the input in a different way than DOMPurify did, so keep its output
	return clean;
};

const describe = (removed: RemovedElement | RemovedAttribute) =>
	"attribute" in removed
		? `the attribute "${removed.attribute?.name}" of <${removed.from.nodeName.toLowerCase()}>`
		: `the element <${removed.element.nodeName.toLowerCase()}>`;
