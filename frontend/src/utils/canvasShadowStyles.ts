/**
 * Copies the editor stylesheets into a canvas shadow root.
 *
 * A shadow root does not inherit document styles, so the block tree renders
 * unstyled without this. Vite serves styles as <style> tags in development and
 * as <link> tags in a build, so this handles both. It also follows later
 * additions, which keeps hot reload working.
 *
 * Fonts need no copy. `@font-face` is document scoped and already applies
 * inside every shadow tree.
 */

const STYLE_SOURCES = 'style, link[rel="stylesheet"]';

class ShadowStyleSync {
	private container = document.createElement("div");
	private observer: MutationObserver | null = null;
	private pendingSync = 0;

	constructor(private root: ShadowRoot) {
		this.container.style.display = "contents";
	}

	start() {
		this.root.prepend(this.container);
		this.copyStyles();
		this.observer = new MutationObserver(() => this.scheduleSync());
		this.observer.observe(document.head, { childList: true, subtree: true, characterData: true });
	}

	stop() {
		this.observer?.disconnect();
		this.observer = null;
		cancelAnimationFrame(this.pendingSync);
		this.container.remove();
	}

	/** Batch the bursts of head mutations that hot reload produces. */
	private scheduleSync() {
		cancelAnimationFrame(this.pendingSync);
		this.pendingSync = requestAnimationFrame(() => this.copyStyles());
	}

	private copyStyles() {
		const sources = document.querySelectorAll<HTMLElement>(STYLE_SOURCES);
		this.container.replaceChildren(...Array.from(sources, (source) => source.cloneNode(true)));
	}
}

export { ShadowStyleSync };
