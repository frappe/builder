export type CanvasFramePoint = {
	x: number;
	y: number;
};

type CanvasDragMove = {
	event: MouseEvent;
	point: CanvasFramePoint;
	startPoint: CanvasFramePoint;
	movementX: number;
	movementY: number;
};

type CanvasDragOptions = {
	cursor?: string;
	onMove: (move: CanvasDragMove) => void;
	onEnd?: (event: MouseEvent) => void;
};

const forwardedEventSources = new WeakMap<Event, Event>();

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

export function getEventSource(event: Event): Event {
	return forwardedEventSources.get(event) || event;
}

export function getEventTarget(event: Event): EventTarget | null {
	return getEventSource(event).target || event.target;
}

export function getEventDocument(event: Event): Document {
	const target = getEventTarget(event) as { nodeType?: number; ownerDocument?: Document } | null;
	if (target?.nodeType === 9) return target as unknown as Document;
	return target?.ownerDocument || document;
}

export function getEventPointInEditor(event: MouseEvent): CanvasFramePoint {
	const source = getEventSource(event) as MouseEvent;
	return framePointToEditor(getEventDocument(event), {
		x: source.clientX,
		y: source.clientY,
	});
}

export function getEventPointInDocument(event: MouseEvent, doc: Document): CanvasFramePoint {
	const point = getEventPointInEditor(event);
	const frame = getFrameElement(doc);
	return frame ? editorPointToFrame(frame, point) : point;
}

export function startCanvasDrag(
	startEvent: MouseEvent,
	target: Element,
	{ cursor, onMove, onEnd }: CanvasDragOptions,
) {
	const targetDocument = getElementDocument(target);
	const listenerDocument = getFrameElement(targetDocument)?.ownerDocument || targetDocument;
	const startPoint = getEventPointInDocument(startEvent, targetDocument);
	const previousCursor = targetDocument.body.style.cursor;

	if (cursor) targetDocument.body.style.cursor = cursor;

	const stop = () => {
		listenerDocument.removeEventListener("mousemove", handleMove);
		listenerDocument.removeEventListener("mouseup", handleEnd);
		if (cursor) targetDocument.body.style.cursor = previousCursor;
	};
	const handleMove = (event: MouseEvent) => {
		const point = getEventPointInDocument(event, targetDocument);
		onMove({
			event,
			point,
			startPoint,
			movementX: point.x - startPoint.x,
			movementY: point.y - startPoint.y,
		});
	};
	const handleEnd = (event: MouseEvent) => {
		stop();
		onEnd?.(event);
	};

	listenerDocument.addEventListener("mousemove", handleMove);
	listenerDocument.addEventListener("mouseup", handleEnd);
	return stop;
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

const bubblingMouseEventTypes = [
	"auxclick",
	"click",
	"contextmenu",
	"dblclick",
	"mousedown",
	"mousemove",
	"mouseout",
	"mouseover",
	"mouseup",
] as const;

const keyboardEventTypes = ["keydown", "keypress", "keyup"] as const;
const clipboardEventTypes = ["copy", "cut", "paste"] as const;
const dragEventTypes = [
	"drag",
	"dragend",
	"dragenter",
	"dragleave",
	"dragover",
	"dragstart",
	"drop",
] as const;

function getForwardedMouseEventInit(event: MouseEvent, doc: Document): MouseEventInit {
	const point = framePointToEditor(doc, { x: event.clientX, y: event.clientY });
	return {
		bubbles: true,
		cancelable: event.cancelable,
		composed: true,
		view: window,
		detail: event.detail,
		screenX: event.screenX,
		screenY: event.screenY,
		clientX: point.x,
		clientY: point.y,
		ctrlKey: event.ctrlKey,
		altKey: event.altKey,
		shiftKey: event.shiftKey,
		metaKey: event.metaKey,
		button: event.button,
		buttons: event.buttons,
		relatedTarget: event.relatedTarget,
	};
}

export function forwardFrameEvents(doc: Document, iframe: HTMLIFrameElement) {
	const frameTarget: EventTarget = doc.defaultView || doc;

	const forward = (source: Event, forwarded: Event) => {
		forwardedEventSources.set(forwarded, source);
		if (source.target) {
			// Outer listeners and third-party shortcuts should still see the original editable target.
			Object.defineProperty(forwarded, "target", {
				configurable: true,
				value: source.target,
			});
		}
		if (!iframe.dispatchEvent(forwarded)) source.preventDefault();
	};

	const forwardMouse = (event: MouseEvent) => {
		forward(event, new MouseEvent(event.type, getForwardedMouseEventInit(event, doc)));
	};

	const forwardWheel = (event: WheelEvent) => {
		forward(
			event,
			new WheelEvent(event.type, {
				...getForwardedMouseEventInit(event, doc),
				deltaX: event.deltaX,
				deltaY: event.deltaY,
				deltaZ: event.deltaZ,
				deltaMode: event.deltaMode,
			}),
		);
	};

	const forwardDrag = (event: DragEvent) => {
		forward(
			event,
			new DragEvent(event.type, {
				...getForwardedMouseEventInit(event, doc),
				dataTransfer: event.dataTransfer,
			}),
		);
	};

	const forwardKeyboard = (event: KeyboardEvent) => {
		forward(
			event,
			new KeyboardEvent(event.type, {
				bubbles: true,
				cancelable: event.cancelable,
				composed: true,
				key: event.key,
				code: event.code,
				location: event.location,
				repeat: event.repeat,
				isComposing: event.isComposing,
				ctrlKey: event.ctrlKey,
				altKey: event.altKey,
				shiftKey: event.shiftKey,
				metaKey: event.metaKey,
			}),
		);
	};

	const forwardClipboard = (event: ClipboardEvent) => {
		forward(
			event,
			new ClipboardEvent(event.type, {
				bubbles: true,
				cancelable: event.cancelable,
				composed: true,
				clipboardData: event.clipboardData,
			}),
		);
	};

	const listeners: Array<
		[types: readonly string[], listener: EventListener, options?: AddEventListenerOptions]
	> = [
		[bubblingMouseEventTypes, forwardMouse as EventListener],
		[["wheel"], forwardWheel as EventListener, { passive: false }],
		[dragEventTypes, forwardDrag as EventListener],
		[keyboardEventTypes, forwardKeyboard as EventListener],
		[clipboardEventTypes, forwardClipboard as EventListener],
	];

	listeners.forEach(([types, listener, options]) => {
		types.forEach((type) => frameTarget.addEventListener(type, listener, options));
	});

	return () => {
		listeners.forEach(([types, listener, options]) => {
			types.forEach((type) => frameTarget.removeEventListener(type, listener, options));
		});
	};
}
