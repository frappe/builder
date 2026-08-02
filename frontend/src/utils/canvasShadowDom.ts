/**
 * Shadow DOM support for canvas breakpoints.
 *
 * Each breakpoint renders its blocks inside a shadow root, so page CSS cannot
 * reach the editor UI. A shadow root shares the viewport, the coordinate space,
 * and the event loop with the editor. Rects, listeners, and drag events need
 * no translation. Only two boundary rules need care:
 *
 * - `event.target` retargets to the host element. Use `getEventTarget`.
 * - `document.querySelector` does not descend into a shadow root. Use `queryCanvas`.
 */

type DelegatedListener = {
	type: string;
	handler: EventListener;
	options?: boolean | AddEventListenerOptions;
};

const canvasShadowRoots = new Set<ShadowRoot>();
const delegatedListeners = new Set<DelegatedListener>();

function registerCanvasShadowRoot(root: ShadowRoot) {
	canvasShadowRoots.add(root);
	delegatedListeners.forEach(({ type, handler, options }) =>
		root.addEventListener(type, handler, options),
	);
	return () => {
		delegatedListeners.forEach(({ type, handler, options }) =>
			root.removeEventListener(type, handler, options),
		);
		canvasShadowRoots.delete(root);
	};
}

/**
 * Listen inside every canvas shadow root, now and for roots added later.
 *
 * Needed for events with a relatedTarget, such as mouseover and mouseout.
 * Event dispatch skips a tree when the target and the relatedTarget retarget
 * to the same node. So a pointer move between two blocks in one canvas never
 * reaches a listener above the host, though entering the canvas from outside
 * still does. That is why the bug looks like "the highlight works once".
 */
function addShadowRootListener(
	type: string,
	handler: EventListener,
	options?: boolean | AddEventListenerOptions,
) {
	const listener = { type, handler, options };
	delegatedListeners.add(listener);
	canvasShadowRoots.forEach((root) => root.addEventListener(type, handler, options));
	return () => {
		delegatedListeners.delete(listener);
		canvasShadowRoots.forEach((root) => root.removeEventListener(type, handler, options));
	};
}

/** The element under the pointer, drilling into every shadow root on the way. */
function elementFromPoint(x: number, y: number): HTMLElement | null {
	let element = document.elementFromPoint(x, y);
	while (element?.shadowRoot) {
		const inner = element.shadowRoot.elementFromPoint(x, y);
		if (!inner || inner === element) break;
		element = inner;
	}
	return element as HTMLElement | null;
}

/** The element the user touched, before the shadow boundary retargets it. */
function getEventTarget(event: Event): HTMLElement | null {
	const path = event.composedPath();
	return ((path[0] as HTMLElement) || (event.target as HTMLElement)) ?? null;
}

/** closest() that keeps walking up through shadow hosts. */
function closestAcrossShadow(element: Element | null, selector: string): HTMLElement | null {
	let current: Element | null = element;
	while (current) {
		const match = current.closest?.(selector);
		if (match) return match as HTMLElement;
		const root = current.getRootNode();
		current = root instanceof ShadowRoot ? root.host : null;
	}
	return null;
}

/** The closest block element for an event, across the shadow boundary. */
function getEventBlockElement(event: Event, selector = ".__builder_component__") {
	return closestAcrossShadow(getEventTarget(event), selector);
}

function searchRoots(): (Document | ShadowRoot)[] {
	return [document, ...canvasShadowRoots];
}

/** querySelector over the editor document and every canvas shadow root. */
function queryCanvas(selector: string): HTMLElement | null {
	for (const root of searchRoots()) {
		const match = root.querySelector<HTMLElement>(selector);
		if (match) return match;
	}
	return null;
}

/** querySelectorAll over the editor document and every canvas shadow root. */
function queryCanvasAll(selector: string): HTMLElement[] {
	return searchRoots().flatMap((root) => Array.from(root.querySelectorAll<HTMLElement>(selector)));
}

/** querySelectorAll under `root`, including any canvas shadow roots inside it. */
function queryAllWithin(root: HTMLElement, selector: string): HTMLElement[] {
	const matches = Array.from(root.querySelectorAll<HTMLElement>(selector));
	for (const shadowRoot of canvasShadowRoots) {
		if (root.contains(shadowRoot.host)) {
			matches.push(...Array.from(shadowRoot.querySelectorAll<HTMLElement>(selector)));
		}
	}
	return matches;
}

/** The shadow root a block renders in, or null if the block is in the light DOM. */
function getShadowRootOf(element: Node): ShadowRoot | null {
	const root = element.getRootNode();
	return root instanceof ShadowRoot ? root : null;
}

export {
	addShadowRootListener,
	closestAcrossShadow,
	elementFromPoint,
	getEventBlockElement,
	getEventTarget,
	getShadowRootOf,
	queryAllWithin,
	queryCanvas,
	queryCanvasAll,
	registerCanvasShadowRoot,
};
