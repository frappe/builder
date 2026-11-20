import { useEventListener } from "@vueuse/core";
import { ref } from "vue";

// how close to the bottom still counts as reading the latest output
const NEAR_BOTTOM = 40;

/** The chat transcript's scroll. It follows new output while the reader is at the
 * bottom, and leaves them where they are once they scroll up to read. */
export class ChatScroll {
	readonly container = ref<HTMLElement | null>(null);
	private following = true;
	private lastTop = 0;
	private frame = 0;
	// scrolling a display:none container (closed tab) is a no-op; park and replay
	private pending = false;

	constructor() {
		useEventListener(this.container, "scroll", this.onScroll, { passive: true });
	}

	/** New output landed: keep the reader on it if they were following. */
	follow() {
		if (this.following) this.schedule();
	}

	/** The reader asked for the latest (sent a message, opened a chat): follow again. */
	toLatest() {
		this.following = true;
		this.schedule();
	}

	flushPending = () => {
		if (!this.pending) return;
		this.pending = false;
		this.follow();
	};

	/** Only scrolling up stops following. Content growing under the reader, or our own
	 * scroll landing after more arrived, leaves scrollTop where it was or moves it down. */
	private onScroll = () => {
		const el = this.container.value;
		if (!el) return;
		const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
		if (el.scrollTop < this.lastTop && distance > 1) this.following = false;
		else if (distance <= NEAR_BOTTOM) this.following = true;
		this.lastTop = el.scrollTop;
	};

	/** At most once a frame: streaming calls this per token, and each scroll forces
	 * a layout. The frame lands after Vue has patched the DOM. */
	private schedule() {
		if (this.frame) return;
		this.frame = requestAnimationFrame(() => {
			this.frame = 0;
			if (!this.following) return;
			const el = this.container.value;
			if (!el || el.clientHeight === 0) {
				this.pending = true;
				return;
			}
			el.scrollTop = el.scrollHeight;
			this.lastTop = el.scrollTop;
		});
	}
}
