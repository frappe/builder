import { builderSettings } from "@/data/builderSettings";

export type ScriptCleanup = () => void;
export type ComponentClientScript = {
	key: string;
	element: HTMLElement;
	breakpoint: string;
	css: string;
	javascript: string;
	componentData: Record<string, any>;
	props: Record<string, any>;
};
export type ComponentClientScriptEmulator = (script: ComponentClientScript) => ScriptCleanup;

type ScriptContext = {
	componentData?: Record<string, any>;
	props?: Record<string, any>;
};

function createEvents(defaultTarget: EventTarget) {
	return {
		dispatch(name: string, data: any, target: EventTarget = defaultTarget) {
			target.dispatchEvent(new CustomEvent(name, { detail: data }));
		},
		listen(name: string, callback: (data: any, event: Event) => void, target: EventTarget = defaultTarget) {
			const handler = (event: Event) => callback((event as CustomEvent).detail, event);
			target.addEventListener(name, handler);
			return () => target.removeEventListener(name, handler);
		},
	};
}

function createScriptFunction(userScript: string) {
	return new Function(
		"context",
		`with (context) {
			return (async function(component_data, props) { ${userScript} })
				.call(thisRef, component_data, props);
		}`,
	);
}

function executeClientScriptUnrestricted(
	thisElement: HTMLElement | null,
	userScript: string,
	{ componentData = {}, props = {} }: ScriptContext = {},
): ScriptCleanup {
	if (!thisElement || !userScript.trim()) return () => {};

	try {
		const fn = createScriptFunction(userScript);
		const cleanup = fn({
			component_data: componentData,
			document,
			events: createEvents(document),
			props,
			thisRef: thisElement,
		});
		if (typeof cleanup !== "function") return () => {};
		return () => {
			try {
				cleanup.call(thisElement);
			} catch (error) {
				console.error("Error cleaning up user script (unrestricted):", error);
			}
		};
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
): ScriptCleanup {
	if (!thisElement || !sandboxRoot || !userScript.trim()) return () => {};

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
			if (val instanceof Node) return wrap(val);
			if (val instanceof NamedNodeMap || val instanceof DOMTokenList || val instanceof CSSStyleDeclaration)
				return wrap(val as any);

			if (val instanceof NodeList || val instanceof HTMLCollection) {
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

	const context = {
		document: proxiedRoot,
		events: createEvents(proxiedRoot),
		thisRef: proxiedThis,
		props,
		component_data: componentData,
		// Escape hatches blocked
		window: undefined,
		globalThis: undefined,
		eval: undefined,
		Function: undefined,
		setTimeout: undefined,
		setInterval: undefined,
	};

	try {
		const fn = createScriptFunction(userScript);
		const userCleanup = fn(context);
		return () => {
			eventListeners.forEach(({ target, type, listener, options }) => {
				target.removeEventListener(type, listener, options);
			});
			if (typeof userCleanup === "function") {
				try {
					userCleanup.call(proxiedThis);
				} catch (error) {
					console.error("Error cleaning up user script (restricted):", error);
				}
			}
		};
	} catch (error) {
		console.error("Error in user script (restricted):", error);
		return () => {
			eventListeners.forEach(({ target, type, listener, options }) => {
				target.removeEventListener(type, listener, options);
			});
		};
	}
}

export {
	executeClientScriptRestricted,
	executeClientScriptUnrestricted,
};
