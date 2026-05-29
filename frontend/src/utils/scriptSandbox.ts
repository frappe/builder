// Execution of user-provided block client scripts.
// Extracted from helpers.ts; re-exported there for backwards compatibility.

import { builderSettings } from "@/data/builderSettings";

function executeBlockClientScriptUnrestricted(
	blockUid: string,
	breakpoint: string,
	userScript: string,
	props: Record<string, any> = {},
) {
	const thisElement = document.querySelector(
		`[data-block-uid='${blockUid}'][data-breakpoint=${breakpoint}]`,
	) as HTMLElement;

	const context = {
		thisRef: thisElement,
		props,
	};

	const fn = new Function(
		"context",
		`with (context) {
			return (function() { ${userScript} }).call(thisRef);
		}`,
	);

	try {
		document.querySelectorAll(`[data-created-by='${blockUid}']`).forEach((el) => el.remove());
		fn.call(thisElement, context);
	} catch (e) {
		console.error("Error in user script (unrestricted):", e);
		// toast.warning("An error occurred while executing block script: " + (e instanceof Error ? e.message : ""));
	}
}

/**
 * Tries to execute user-provided script in a safer environment, (but not guarantee) restricting access to certain DOM properties and methods.
 * It makes the editor canvas as the root (document), and thus limits the script's ability to manipulate the broader document.
 * It tries to restrict escape hatches which could be used to access the global window or document objects.
 * It tries to `wrap` all returned DOM nodes and collections to ensure they are also proxied.
 * The `wrap` function creates proxies for DOM elements to intercept property access and method calls.
 *
 * @param blockId - The ID of the block element to which the script is associated.
 * @param userScript - The user-provided JavaScript code to execute.
 * @param props - An optional object containing properties to be made available in the script's context.
 */

function executeBlockClientScriptRestricted(
	blockUid: string,
	breakpoint: string,
	userScript: string,
	props: Record<string, any> = {},
) {
	const cache = new WeakMap();

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

	function wrap(value: Element | Node) {
		if (value === null || typeof value !== "object") return value;
		if (cache.has(value)) return cache.get(value);

		const proxy = new Proxy(value, handler);
		cache.set(value, proxy);
		return proxy;
	}

	const handler = {
		get(target: Element, prop: string, receiver: any) {
			if (BLOCKED_GET.has(prop)) return undefined;

			// Always pass `target` (not the proxy) as the receiver so that native DOM
			// getters (e.g. tagName, nodeType, children) run with the correct `this`.
			// Passing the Proxy as receiver causes "Illegal invocation" in those cases.
			let val = Reflect.get(target, prop, target);

			// Wrap DOM returns
			if (val instanceof Node) return wrap(val);
			if (val instanceof NamedNodeMap || val instanceof DOMTokenList || val instanceof CSSStyleDeclaration)
				return wrap(val as any);

			if (val instanceof NodeList || val instanceof HTMLCollection) {
				return Array.from(val, wrap);
			}

			// Wrap functions (methods)
			if (typeof val === "function") {
				// disallow eventListeners
				if (prop === "addEventListener" || prop === "removeEventListener") {
					// disallow clicks
					return (...args: any[]) => {
						const eventType = args[0];
						const disallowClicks = Boolean(builderSettings.doc?.block_click_handlers);
						if (disallowClicks && (eventType === "click" || eventType === "dblclick")) {
							throw new Error(`Blocked: cannot add/remove ${eventType} event listeners`);
						}
						const realArgs = args.map((a) => cache.get(a) || a);
						return val.apply(target, realArgs);
					};
				}
				return (...args) => {
					const realArgs = args.map((a) => cache.get(a) || a);

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

		set(target: Element, prop: string, value: any) {
			if (BLOCKED_SET.has(prop)) {
				throw new Error(`Blocked: cannot set ${prop}`);
			}

			// Allow normal DOM props like src, value, className, id, etc.
			try {
				return Reflect.set(target as any, prop as any, value);
			} catch {
				return false;
			}
		},
	};

	const sandboxRoot = document.querySelector("[data-block-id='root']") as HTMLElement;
	const thisElement = document.querySelector(
		`[data-block-uid='${blockUid}'][data-breakpoint='${breakpoint}']`,
	) as HTMLElement;

	const proxiedRoot = wrap(sandboxRoot);
	const proxiedThis = wrap(thisElement);

	const context = {
		document: proxiedRoot,
		thisRef: proxiedThis,
		props,
		// Escape hatches blocked
		window: undefined,
		globalThis: undefined,
		eval: undefined,
		Function: undefined,
		setTimeout: undefined,
		setInterval: undefined,
	};

	const fn = new Function(
		"context",
		`with (context) {
			return (function() { ${userScript} }).call(thisRef);
		}`,
	);

	try {
		fn.call(proxiedThis, context);
	} catch (e) {
		console.error("Error in user script:", e);
		// toast.warning("An error occurred while executing block script: " + (e instanceof Error ? e.message : ""));
	}
}

export { executeBlockClientScriptUnrestricted, executeBlockClientScriptRestricted };
