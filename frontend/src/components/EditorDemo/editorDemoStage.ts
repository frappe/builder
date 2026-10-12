import { runPageScripts } from "@/components/EditorDemo/pageScripts";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { editorDemo, postToLauncher } from "@/utils/editorDemo";
import { until } from "@vueuse/core";

type Rect = { left: number; top: number; width: number; height: number };
type CanvasView = { scale: number; translateX: number; translateY: number };

const EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)";
const EASE_IN_OUT = "cubic-bezier(0.65, 0, 0.35, 1)";
// room around the page once it settles into the canvas
const FIT_PADDING = 48;
const OFFSCREEN = { toolbar: "translateY(-100%)", left: "translateX(-100%)", right: "translateX(100%)" };

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
const motion = (ms: number) => (matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : ms);

/**
 * Hands the visitor over from the published page to the editor and back. The canvas starts
 * as a 1:1 copy of what they were looking at, anchored on the link they clicked, then the
 * chrome slides in while the page settles to fit, so the page turns into the editor in place.
 */
class EditorDemoStage {
	framed = window.parent !== window;
	private scrollY = 0;
	// how far the published layout sits below the canvas copy, measured at the clicked link
	private layoutOffset = 0;
	private anchorBlockId?: string;
	private started?: Promise<unknown>;

	/** Lay the page out at the launcher's width, then run its own scripts on the canvas. */
	start() {
		this.started ??= this.whenCanvasReady().then(async () => {
			const desktop = this.canvas.canvasProps.breakpoints.find((bp) => bp.device === "desktop");
			if (desktop && this.framed) desktop.width = window.innerWidth;
			await nextFrame();
			runPageScripts(editorDemo?.scripts || [], this.page);
		});
		return this.started;
	}

	async prepare(scrollY: number, target?: Rect, dark = false) {
		await this.start();
		// match the theme the page is showing, so the hand-off does not flip it
		const builderStore = useBuilderStore();
		builderStore.isDark = builderStore.canvasDarkMode = dark;
		this.canvas.clearSelection();
		this.setOverlaysHidden(true);
		this.slidePanels("out", 0);
		this.scrollY = scrollY;
		this.applyView(this.viewAt(scrollY));
		await nextFrame();
		const anchor = target && findAnchor(target);
		this.anchorBlockId = anchor?.dataset.blockId;
		this.layoutOffset = 0;
		if (anchor && target) {
			const rect = anchor.getBoundingClientRect();
			const translateX = this.canvas.canvasProps.translateX + target.left - rect.left;
			this.layoutOffset = target.top - rect.top;
			this.scrollY -= this.layoutOffset;
			this.applyView({ ...this.viewAt(this.scrollY), translateX });
			await nextFrame();
		}
		postToLauncher({ type: "ready" });
	}

	async play() {
		const duration = motion(640);
		this.animateView(this.fitView(), duration, EASE_OUT);
		this.slidePanels("in", motion(520));
		// the ease-out has all but landed by now, so selecting here keeps the motion going
		await wait(duration * 0.55);
		this.setOverlaysHidden(false);
		const anchor = this.anchorBlockId && this.canvas.findBlock(this.anchorBlockId);
		if (anchor) this.canvas.selectBlock(anchor);
	}

	async exit() {
		if (!this.framed) return location.assign(`/${editorDemo?.page.route || ""}`);
		const scrollY = this.scrollYAtFitTop();
		const duration = motion(560);
		this.canvas.clearSelection();
		this.setOverlaysHidden(true);
		this.animateView(this.viewAt(scrollY), duration, EASE_IN_OUT);
		this.slidePanels("out", motion(420));
		await wait(duration + 20);
		postToLauncher({ type: "exit", scrollY: scrollY + this.layoutOffset });
	}

	private get canvas() {
		return useCanvasStore().activeCanvas as NonNullable<ReturnType<typeof useCanvasStore>["activeCanvas"]>;
	}

	private get page() {
		return document.querySelector<HTMLElement>(".canvas-container [data-breakpoint='desktop']")!;
	}

	private get canvasElement() {
		return this.page.parentElement!;
	}

	private get container() {
		return this.canvasElement.closest(".canvas-container")!.getBoundingClientRect();
	}

	private async whenCanvasReady() {
		const canvasStore = useCanvasStore();
		const pageStore = usePageStore();
		// until() looks again only when something reactive changes, and readyState is not
		// reactive: with it in the condition, a canvas that is ready before the page has
		// finished loading is never noticed, and the demo never opens
		if (document.readyState !== "complete") {
			await new Promise((resolve) => window.addEventListener("load", resolve, { once: true }));
		}
		await until(
			() => canvasStore.activeCanvas?.canvasProps.settingCanvas === false && !pageStore.settingPage,
		).toBe(true);
		await document.fonts.ready;
	}

	private applyView(view: CanvasView) {
		Object.assign(this.canvas.canvasProps, view);
	}

	private animateView(view: CanvasView, duration: number, easing: string) {
		const element = this.canvasElement;
		element.style.transition = `transform ${duration}ms ${easing}`;
		this.applyView(view);
		setTimeout(() => (element.style.transition = ""), duration + 20);
	}

	// the canvas' own chrome (breakpoint label, zoom pill) hides while it pans or scales
	private setOverlaysHidden(hidden: boolean) {
		this.canvas.canvasProps.scaling = hidden;
		this.canvas.canvasProps.panning = hidden;
	}

	/**
	 * Where the canvas would sit untransformed. It scales around its top center, so a
	 * page point p lands on screen at left + width/2 + scale * (p.x + translateX - width/2),
	 * top + scale * (p.y + translateY).
	 */
	private origin() {
		const { scale, translateX, translateY } = this.canvas.canvasProps;
		const rect = this.canvasElement.getBoundingClientRect();
		const width = this.canvasElement.offsetWidth;
		return {
			left: rect.left - width / 2 - scale * (translateX - width / 2),
			top: rect.top - scale * translateY,
		};
	}

	private viewAt(scrollY: number): CanvasView {
		const { left, top } = this.origin();
		return { scale: 1, translateX: -left, translateY: -top - scrollY };
	}

	private fitView(): CanvasView {
		const scale = Math.min(1, (this.container.width - FIT_PADDING * 2) / this.canvasElement.offsetWidth);
		const translateY = (this.container.top + FIT_PADDING - this.origin().top) / scale - this.scrollY;
		return { scale, translateX: 0, translateY };
	}

	// the inverse of fitView, so opening and closing straight away lands where it started
	private scrollYAtFitTop() {
		const { scale, translateY } = this.canvas.canvasProps;
		return Math.max(
			0,
			Math.round((this.container.top + FIT_PADDING - this.origin().top) / scale - translateY),
		);
	}

	private slidePanels(direction: "in" | "out", duration: number) {
		for (const [panel, offscreen] of Object.entries(OFFSCREEN)) {
			const element = document.querySelector<HTMLElement>(`[data-panel="${panel}"]`);
			if (!element) continue;
			const moving = direction === "in";
			element.style.transform = moving ? "" : offscreen;
			element.animate(
				{ transform: moving ? [offscreen, "none"] : ["none", offscreen] },
				{
					duration,
					delay: moving ? motion(80) : 0,
					easing: moving ? EASE_OUT : EASE_IN_OUT,
					fill: "backwards",
				},
			);
		}
	}
}

// the canvas copy of the link the visitor clicked, nearest to where they clicked it
function findAnchor(target: Rect) {
	const distance = (element: Element) => {
		const rect = element.getBoundingClientRect();
		return Math.hypot(rect.left - target.left, rect.top - target.top);
	};
	const links = document.querySelectorAll(".canvas [href='#editor-demo'], .canvas [data-editor-demo]");
	return [...links]
		.map((link) => link.closest<HTMLElement>("[data-block-id]"))
		.filter((block): block is HTMLElement => Boolean(block))
		.sort((a, b) => distance(a) - distance(b))[0];
}

export const editorDemoStage = new EditorDemoStage();
