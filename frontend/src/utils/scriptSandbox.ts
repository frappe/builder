import { builderSettings } from "@/data/builderSettings";

export type ScriptCleanup = () => void;
export type BlockClientScriptRuntime = {
	key: string;
	element: HTMLElement;
	breakpoint: string;
	css: string;
	javascript: string;
	componentData: Record<string, any>;
	props: Record<string, any>;
};
export type BlockClientScriptEmulator = (script: BlockClientScriptRuntime) => ScriptCleanup;

type ScriptContext = {
	componentData?: Record<string, any>;
	props?: Record<string, any>;
};

type PageScriptContext = {
	pageData?: Record<string, any>;
};

function createEvents(defaultTarget: EventTarget, targetWindow: Window) {
	const CustomEventConstructor = (targetWindow as any).CustomEvent as typeof CustomEvent;
	return {
		dispatch(name: string, data: any, target: EventTarget = defaultTarget) {
			target.dispatchEvent(new CustomEventConstructor(name, { detail: data }));
		},
		listen(name: string, callback: (data: any, event: Event) => void, target: EventTarget = defaultTarget) {
			const handler = (event: Event) => callback((event as CustomEvent).detail, event);
			target.addEventListener(name, handler);
			return () => target.removeEventListener(name, handler);
		},
	};
}

function createScriptFunction(userScript: string, targetWindow: Window, pageScript = false) {
	const FunctionConstructor = (targetWindow as any).Function as FunctionConstructor;
	const parameters = pageScript ? "" : "component_data, props";
	const callArguments = pageScript ? "thisRef" : "thisRef, component_data, props";
	return new FunctionConstructor(
		"context",
		`with (context) {
			return (async function(${parameters}) { ${userScript} })
				.call(${callArguments});
		}`,
	);
}

function createScriptCleanup(
	result: unknown,
	thisArg: unknown,
	mode: "restricted" | "unrestricted",
	onDispose: () => void = () => {},
): ScriptCleanup {
	let disposed = false;
	let resolvedCleanup: unknown;

	const runCleanup = (cleanup: unknown) => {
		if (typeof cleanup !== "function") return;
		try {
			cleanup.call(thisArg);
		} catch (error) {
			console.error(`Error cleaning up user script (${mode}):`, error);
		}
	};

	Promise.resolve(result).then(
		(value) => {
			resolvedCleanup = value;
			if (disposed) runCleanup(value);
		},
		(error) => console.error(`Error in user script (${mode}):`, error),
	);

	return () => {
		if (disposed) return;
		disposed = true;
		onDispose();
		runCleanup(resolvedCleanup);
	};
}

function executeClientScriptUnrestricted(
	thisElement: HTMLElement | null,
	userScript: string,
	{ componentData = {}, props = {} }: ScriptContext = {},
	pageContext: PageScriptContext | null = null,
): ScriptCleanup {
	if (!thisElement || !userScript.trim()) return () => {};

	try {
		const targetDocument = thisElement.ownerDocument;
		const targetWindow = targetDocument.defaultView || window;
		const events = createEvents(targetDocument, targetWindow);
		const isPageScript = pageContext !== null;
		const thisRef = isPageScript ? targetWindow : thisElement;
		const context = isPageScript
			? {
					document: targetDocument,
					events,
					page_data: pageContext.pageData ?? {},
					thisRef,
			  }
			: {
					component_data: componentData,
					document: targetDocument,
					events,
					props,
					thisRef,
			  };

		if (isPageScript) {
			Object.assign(targetWindow, {
				events,
				page_data: pageContext.pageData ?? {},
			});
		}

		const fn = createScriptFunction(userScript, targetWindow, isPageScript);
		const cleanup = fn(context);
		return createScriptCleanup(cleanup, thisRef, "unrestricted");
	} catch (error) {
		console.error("Error in user script (unrestricted):", error);
		return () => {};
	}
}

/**
 * Executes a user script with the canvas exposed as document and proxies DOM values
 * to restrict common escape hatches into the broader editor document.
 */
function executeClientScriptRestricted(
	thisElement: HTMLElement | null,
	sandboxRoot: HTMLElement | null,
	userScript: string,
	{ componentData = {}, props = {} }: ScriptContext = {},
	pageContext: PageScriptContext | null = null,
): ScriptCleanup {
	if (!thisElement || !sandboxRoot || !userScript.trim()) return () => {};
	const targetDocument = thisElement.ownerDocument;
	const targetWindow = targetDocument.defaultView || window;
	const FrameNode = targetWindow.Node;
	const FrameNamedNodeMap = targetWindow.NamedNodeMap;
	const FrameDOMTokenList = targetWindow.DOMTokenList;
	const FrameCSSStyleDeclaration = targetWindow.CSSStyleDeclaration;
	const FrameNodeList = targetWindow.NodeList;
	const FrameHTMLCollection = targetWindow.HTMLCollection;

	const cache = new WeakMap<object, any>();
	const rawValues = new WeakMap<object, object>();
	const eventListeners: Array<{
		target: Element;
		type: string;
		listener: EventListenerOrEventListenerObject;
		options?: boolean | AddEventListenerOptions;
	}> = [];

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

	function wrap(value: any): any {
		if (value === null || typeof value !== "object") return value;
		if (cache.has(value)) return cache.get(value);

		const proxy = new Proxy(value, handler);
		cache.set(value, proxy);
		rawValues.set(proxy, value);
		return proxy;
	}

	function unwrap(value: any) {
		return value !== null && typeof value === "object" ? rawValues.get(value) || value : value;
	}

	const handler = {
		get(target: Element, prop: string | symbol) {
			if (typeof prop === "string" && BLOCKED_GET.has(prop)) return undefined;

			// Always pass `target` (not the proxy) as the receiver so that native DOM
			// getters (e.g. tagName, nodeType, children) run with the correct `this`.
			// Passing the Proxy as receiver causes "Illegal invocation" in those cases.
			const val = Reflect.get(target, prop, target);

			// Wrap DOM returns
			if (val instanceof FrameNode) return wrap(val);
			if (
				val instanceof FrameNamedNodeMap ||
				val instanceof FrameDOMTokenList ||
				val instanceof FrameCSSStyleDeclaration
			)
				return wrap(val as any);

			if (val instanceof FrameNodeList || val instanceof FrameHTMLCollection) {
				return Array.from(val, wrap);
			}

			// Wrap functions (methods)
			if (typeof val === "function") {
				if (prop === "addEventListener" || prop === "removeEventListener") {
					return (
						type: string,
						listener: EventListenerOrEventListenerObject,
						options?: boolean | AddEventListenerOptions,
					) => {
						if (builderSettings.doc?.restrict_click_handlers && (type === "click" || type === "dblclick")) {
							throw new Error(`Blocked: cannot add/remove ${type} event listeners`);
						}
						const realListener = unwrap(listener);
						const result = val.call(target, type, realListener, options);
						if (prop === "addEventListener") {
							eventListeners.push({ target, type, listener: realListener, options });
						}
						return result;
					};
				}
				return (...args: any[]) => {
					const realArgs = args.map(unwrap);

					// Do not allow inserting nodes outside the sandbox
					for (const a of realArgs) {
						if (a instanceof FrameNode && !sandboxRoot.contains(a)) {
							throw new Error("Blocked: external node insertion");
						}
					}

					const result = val.apply(target, realArgs);
					return wrap(result);
				};
			}

			return val; // primitive allowed
		},

		set(target: Element, prop: string | symbol, value: any) {
			if (typeof prop === "string" && BLOCKED_SET.has(prop)) {
				throw new Error(`Blocked: cannot set ${String(prop)}`);
			}

			// Allow normal DOM props like src, value, className, id, etc.
			try {
				return Reflect.set(target, prop, unwrap(value), target);
			} catch {
				return false;
			}
		},
	};

	const proxiedRoot = wrap(sandboxRoot);
	const proxiedThis = wrap(thisElement);
	const isPageScript = pageContext !== null;
	const thisRef = isPageScript ? proxiedRoot : proxiedThis;

	const restrictedGlobals = {
		document: proxiedRoot,
		events: createEvents(proxiedRoot, targetWindow),
		thisRef,
		// Escape hatches blocked
		window: undefined,
		globalThis: undefined,
		eval: undefined,
		Function: undefined,
		setTimeout: undefined,
		setInterval: undefined,
	};
	const context = isPageScript
		? {
				...restrictedGlobals,
				page_data: pageContext.pageData ?? {},
		  }
		: {
				...restrictedGlobals,
				props,
				component_data: componentData,
		  };

	try {
		const fn = createScriptFunction(userScript, targetWindow, isPageScript);
		const userCleanup = fn(context);
		return createScriptCleanup(userCleanup, thisRef, "restricted", () => {
			eventListeners.forEach(({ target, type, listener, options }) => {
				target.removeEventListener(type, listener, options);
			});
		});
	} catch (error) {
		console.error("Error in user script (restricted):", error);
		return () => {
			eventListeners.forEach(({ target, type, listener, options }) => {
				target.removeEventListener(type, listener, options);
			});
		};
	}
}

function executePageClientScriptUnrestricted(
	canvasRoot: HTMLElement | null,
	userScript: string,
	pageData: Record<string, any>,
) {
	return executeClientScriptUnrestricted(canvasRoot, userScript, {}, { pageData });
}

function executePageClientScriptRestricted(
	canvasRoot: HTMLElement | null,
	userScript: string,
	pageData: Record<string, any>,
) {
	return executeClientScriptRestricted(canvasRoot, canvasRoot, userScript, {}, { pageData });
}

export {
	executeClientScriptRestricted,
	executeClientScriptUnrestricted,
	executePageClientScriptRestricted,
	executePageClientScriptUnrestricted,
};
