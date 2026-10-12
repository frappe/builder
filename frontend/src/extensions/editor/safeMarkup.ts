/**
 * The markup that an extension may put on the canvas.
 *
 * The canvas renders a block in the editor page, outside the sandbox of the
 * extension frame. `innerHTML` goes through `v-html`, and attributes go onto the
 * element. So an `onerror` attribute or a `<script>` element from an extension
 * would run with the session of the user. These checks refuse such markup. The
 * page stores what passes, so the published page gets the same markup.
 *
 * DOMPurify decides what is safe. Each check refuses and does not clean, so the
 * author of the extension sees what the host did not accept.
 *
 * Only the block methods come through here. `data.*` writes documents as they
 * are, so `data.access` is a trusted permission (see `builder/extensions/data.py`).
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

export const readHTML = (value: unknown, field: string) => {
	if (value === undefined) return undefined;
	// a string that starts with <script> puts it in <head>, where DOMPurify neither
	// checks nor reports it. A template parses as `v-html` does, and loads nothing
	const template = document.createElement("template");
	template.innerHTML = anyText(value, field);
	const clean = purifier.sanitize(template.content);
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
