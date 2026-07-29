/**
 * Document and window facades for client scripts in a shadow canvas.
 *
 * A published page gives a client script the real document. In the editor the
 * page renders inside a shadow root, so `document.querySelector` would search
 * the editor UI and find nothing. These facades route DOM lookups to the shadow
 * root, report the breakpoint width, and record listeners and timers so the
 * caller can undo them.
 *
 * These facades emulate. They do not sandbox. A page script still runs in the
 * editor JavaScript realm and can reach the real window through any global it
 * likes. Shadow DOM cannot prevent that. Use scriptSandbox.ts when you need the
 * restricted mode.
 */

type Disposer = () => void;

/** Events a page script waits for that already happened by the time it runs. */
const READY_EVENTS = new Set(["DOMContentLoaded", "load", "readystatechange"]);

const WIDTH_CONDITION = /\((min|max)-width:\s*(\d+(?:\.\d+)?)(px)?\)/gi;

function createFacade<T extends object>(base: T, overrides: object): T {
	return new Proxy(base, {
		get(target, prop) {
			if (prop in overrides) return Reflect.get(overrides, prop);
			const value = Reflect.get(target, prop);
			// native methods throw "Illegal invocation" when called on the proxy
			return typeof value === "function" ? value.bind(target) : value;
		},
		set(target, prop, value) {
			if (prop in overrides) return Reflect.set(overrides, prop, value);
			return Reflect.set(target, prop, value);
		},
	}) as T;
}

class CanvasScriptScope {
	private disposers: Disposer[] = [];
	readonly document: Document;
	readonly window: Window;

	constructor(
		private root: ShadowRoot,
		private breakpointWidth: number,
		private pageData: Record<string, any> = {},
	) {
		this.document = this.createDocumentFacade();
		this.window = this.createWindowFacade();
	}

	/** Undo every listener and timer the scripts registered. */
	dispose() {
		this.disposers.forEach((disposer) => disposer());
		this.disposers = [];
	}

	private track(disposer: Disposer) {
		this.disposers.push(disposer);
	}

	/** The rendered page body, which is the root block. */
	private get pageBody() {
		return this.root.querySelector<HTMLElement>("[data-block-id='root']") ?? this.root.firstElementChild;
	}

	private addRootListener(type: string, listener: EventListenerOrEventListenerObject, options?: any) {
		if (READY_EVENTS.has(type)) {
			const timer = setTimeout(() => (listener as EventListener)(new Event(type)));
			this.track(() => clearTimeout(timer));
			return;
		}
		this.root.addEventListener(type, listener, options);
		this.track(() => this.root.removeEventListener(type, listener, options));
	}

	private createDocumentFacade() {
		const root = this.root;
		const getPageBody = () => this.pageBody;
		const overrides = {
			querySelector: (selector: string) => root.querySelector(selector),
			querySelectorAll: (selector: string) => root.querySelectorAll(selector),
			getElementById: (id: string) => root.getElementById(id),
			getElementsByClassName: (name: string) => root.querySelectorAll(`.${CSS.escape(name)}`),
			getElementsByTagName: (name: string) => root.querySelectorAll(name),
			addEventListener: this.addRootListener.bind(this),
			removeEventListener: (type: string, listener: any, options?: any) =>
				root.removeEventListener(type, listener, options),
			dispatchEvent: (event: Event) => root.dispatchEvent(event),
			readyState: "complete",
			currentScript: null,
			get body() {
				return getPageBody();
			},
			get documentElement() {
				return getPageBody();
			},
		};
		return createFacade(document, overrides);
	}

	/**
	 * A shadow root resolves media queries against the editor viewport, so a
	 * width query would give the same answer on every breakpoint. Answer width
	 * queries from the breakpoint instead and pass everything else through.
	 */
	private matchBreakpointMedia(query: string) {
		WIDTH_CONDITION.lastIndex = 0;
		const conditions = Array.from(query.matchAll(WIDTH_CONDITION));
		if (!conditions.length) return window.matchMedia(query);
		const matches = conditions.every(([, bound, value]) =>
			bound.toLowerCase() === "min" ? this.breakpointWidth >= Number(value) : this.breakpointWidth <= Number(value),
		);
		return { matches, media: query, addEventListener() {}, removeEventListener() {}, onchange: null };
	}

	private createWindowFacade() {
		const overrides = {
			document: this.document,
			// the published page sets this in webpage_scripts.html
			page_data: this.pageData,
			innerWidth: this.breakpointWidth,
			matchMedia: (query: string) => this.matchBreakpointMedia(query),
			addEventListener: (type: string, listener: any, options?: any) => {
				if (READY_EVENTS.has(type)) return this.addRootListener(type, listener, options);
				window.addEventListener(type, listener, options);
				this.track(() => window.removeEventListener(type, listener, options));
			},
			setTimeout: (handler: TimerHandler, delay?: number, ...args: any[]) => {
				const timer = window.setTimeout(handler, delay, ...args);
				this.track(() => window.clearTimeout(timer));
				return timer;
			},
			setInterval: (handler: TimerHandler, delay?: number, ...args: any[]) => {
				const timer = window.setInterval(handler, delay, ...args);
				this.track(() => window.clearInterval(timer));
				return timer;
			},
			requestAnimationFrame: (callback: FrameRequestCallback) => {
				const frame = window.requestAnimationFrame(callback);
				this.track(() => window.cancelAnimationFrame(frame));
				return frame;
			},
		};
		return createFacade(window, overrides);
	}
}

export { CanvasScriptScope };
