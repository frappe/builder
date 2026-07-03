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

function createScriptCleanup(result: unknown, thisArg: unknown): ScriptCleanup {
	let disposed = false;
	let resolvedCleanup: unknown;

	const runCleanup = (cleanup: unknown) => {
		if (typeof cleanup !== "function") return;
		try {
			cleanup.call(thisArg);
		} catch (error) {
			console.error("Error cleaning up client script:", error);
		}
	};

	Promise.resolve(result).then(
		(value) => {
			resolvedCleanup = value;
			if (disposed) runCleanup(value);
		},
		(error) => console.error("Error executing client script:", error),
	);

	return () => {
		if (disposed) return;
		disposed = true;
		runCleanup(resolvedCleanup);
	};
}

function executeClientScript(
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
		return createScriptCleanup(fn(context), thisRef);
	} catch (error) {
		console.error("Error executing client script:", error);
		return () => {};
	}
}

function executePageClientScript(
	canvasRoot: HTMLElement | null,
	userScript: string,
	pageData: Record<string, any>,
) {
	return executeClientScript(canvasRoot, userScript, {}, { pageData });
}

export { executeClientScript, executePageClientScript };
