export type CanvasFramePoint = {
	x: number;
	y: number;
};

export function getElementDocument(element: Element | null): Document {
	return element?.ownerDocument || document;
}

export function getElementWindow(element: Element | null): Window {
	return getElementDocument(element).defaultView || window;
}

export function getComputedStyleFor(element: Element): CSSStyleDeclaration {
	return getElementWindow(element).getComputedStyle(element);
}

export function getFrameElement(doc: Document): HTMLIFrameElement | null {
	const frame = doc.defaultView?.frameElement;
	return frame && frame.tagName === "IFRAME" ? (frame as HTMLIFrameElement) : null;
}

export function getElementRectInEditor(element: Element): DOMRect {
	const rect = element.getBoundingClientRect();
	const frame = getFrameElement(element.ownerDocument);
	if (!frame) return rect;

	const frameRect = frame.getBoundingClientRect();
	const scaleX = frame.clientWidth ? frameRect.width / frame.clientWidth : 1;
	const scaleY = frame.clientHeight ? frameRect.height / frame.clientHeight : 1;

	return new DOMRect(
		frameRect.left + rect.left * scaleX,
		frameRect.top + rect.top * scaleY,
		rect.width * scaleX,
		rect.height * scaleY,
	);
}

export function framePointToEditor(doc: Document, point: CanvasFramePoint): CanvasFramePoint {
	const frame = getFrameElement(doc);
	if (!frame) return point;

	const frameRect = frame.getBoundingClientRect();
	const scaleX = frame.clientWidth ? frameRect.width / frame.clientWidth : 1;
	const scaleY = frame.clientHeight ? frameRect.height / frame.clientHeight : 1;
	return {
		x: frameRect.left + point.x * scaleX,
		y: frameRect.top + point.y * scaleY,
	};
}

export function editorPointToFrame(frame: HTMLIFrameElement, point: CanvasFramePoint): CanvasFramePoint {
	const rect = frame.getBoundingClientRect();
	const scaleX = frame.clientWidth ? rect.width / frame.clientWidth : 1;
	const scaleY = frame.clientHeight ? rect.height / frame.clientHeight : 1;
	return {
		x: (point.x - rect.left) / scaleX,
		y: (point.y - rect.top) / scaleY,
	};
}

export function elementFromEditorPoint(x: number, y: number): Element | null {
	const outerElement = document.elementFromPoint(x, y);
	if (!(outerElement instanceof HTMLIFrameElement)) return outerElement;

	const frameDocument = outerElement.contentDocument;
	if (!frameDocument) return outerElement;
	const point = editorPointToFrame(outerElement, { x, y });
	return frameDocument.elementFromPoint(point.x, point.y) || outerElement;
}

export function isElementLike(value: unknown): value is Element {
	return Boolean(
		value &&
			typeof value === "object" &&
			"nodeType" in value &&
			(value as { nodeType: number }).nodeType === Node.ELEMENT_NODE,
	);
}
