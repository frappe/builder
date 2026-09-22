import { runPageScripts } from "@/components/EditorDemo/pageScripts";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { editorDemo, postToLauncher } from "@/utils/editorDemo";
import { until } from "@vueuse/core";
import { nextTick, ref } from "vue";

type Rect = { left: number; top: number; width: number; height: number };
type CanvasView = { scale: number; translateX: number; translateY: number };

const EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)";
const EASE_IN_OUT = "cubic-bezier(0.65, 0, 0.35, 1)";
const INTRO_MS = 640;
const OUTRO_MS = 560;
// room around the page once it settles into the canvas
const FIT_PADDING = 48;
const PANEL_OFFSCREEN = {
	toolbar: "translateY(-100%)",
	left: "translateX(-100%)",
	right: "translateX(100%)",
};

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
const motion = (ms: number) => (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : ms);

/**
 * Hands the visitor over from the published page to the editor and back. The canvas
 * starts as a 1:1 copy of what they were looking at, then the chrome slides in while
 * the page settles to fit, so the page seems to turn into the editor in place.
 */
class EditorDemoStage {
	isOpen = ref(false);
	private scrollY = 0;
	// how far the published layout sits below the canvas copy, measured at the clicked link
	private layoutOffset = 0;
	private target: Rect | null = null;
	private targetBlockId: string | null = null;
	private started: Promise<unknown> | null = null;

	get framed() {
		return window.parent !== window;
	}

	/** Once the canvas has the page, run the page's own scripts on it, as the live page does. */
	start() {
		this.started ??= this.whenCanvasReady().then(() => {
			runPageScripts(editorDemo?.scripts || [], this.pageElement);
			return nextFrame();
		});
		return this.started;
	}

	/**
	 * Mirror the launcher's view of the page, scrolled to scrollY, with the chrome tucked away.
	 * Page scripts can shift the published layout a little, so the clicked link is what gets
	 * lined up exactly: it is where the visitor is looking.
	 */
	async prepare(scrollY: number, target: Rect | null) {
		this.scrollY = scrollY;
		this.layoutOffset = 0;
		this.target = target;
		await this.start();
		this.canvas.clearSelection();
		this.setOverlaysHidden(true);
		Object.entries(PANEL_OFFSCREEN).forEach(([panel, offscreen]) => {
			const element = getPanel(panel);
			if (element) element.style.transform = offscreen;
		});
		this.applyView(this.viewAt(this.scrollY));
		await nextFrame();
		const anchor = this.target && findAnchor(this.target);
		this.targetBlockId = anchor?.dataset.blockId || null;
		if (anchor && this.target) {
			const rect = anchor.getBoundingClientRect();
			const translateX = this.canvas.canvasProps.translateX + this.target.left - rect.left;
			this.layoutOffset = this.target.top - rect.top;
			this.scrollY -= this.layoutOffset;
			this.applyView({ ...this.viewAt(this.scrollY), translateX });
			await nextFrame();
		}
		await imagesInView();
		postToLauncher({ type: "ready" });
	}

	async play() {
		const duration = motion(INTRO_MS);
		this.canvasElement.style.transition = `transform ${duration}ms ${EASE_OUT}`;
		this.applyView(this.fitView(this.scrollY));
		this.slidePanels("in", motion(520));
		this.isOpen.value = true;
		// the ease-out has all but landed by now, so selecting here keeps the motion going
		await wait(duration * 0.55);
		this.setOverlaysHidden(false);
		const block = this.targetBlockId && this.canvas.findBlock(this.targetBlockId);
		if (block) this.canvas.selectBlock(block);
		await wait(duration * 0.45 + 20);
		this.canvasElement.style.transition = "";
	}

	async exit() {
		if (!this.framed) {
			window.location.assign(`/${editorDemo?.page.route || ""}`);
			return;
		}
		const scrollY = this.scrollYAtFitTop();
		const duration = motion(OUTRO_MS);
		this.isOpen.value = false;
		this.canvas.clearSelection();
		this.setOverlaysHidden(true);
		this.canvasElement.style.transition = `transform ${duration}ms ${EASE_IN_OUT}`;
		this.applyView(this.viewAt(scrollY));
		this.slidePanels("out", motion(420));
		await wait(duration + 20);
		this.canvasElement.style.transition = "";
		postToLauncher({ type: "exit", scrollY: scrollY + this.layoutOffset });
	}

	/** Render the page at the launcher's width, so text wraps exactly as it did there. */
	matchLauncherWidth() {
		const desktop = this.canvas.canvasProps.breakpoints.find((bp) => bp.device === "desktop");
		if (desktop && this.framed) desktop.width = window.innerWidth;
	}

	private get canvas() {
		return useCanvasStore().activeCanvas as NonNullable<ReturnType<typeof useCanvasStore>["activeCanvas"]>;
	}

	private get pageElement() {
		return document.querySelector<HTMLElement>(
			".canvas-container [data-breakpoint='desktop']",
		) as HTMLElement;
	}

	private get canvasElement() {
		return this.pageElement.parentElement as HTMLElement;
	}

	private async whenCanvasReady() {
		const canvasStore = useCanvasStore();
		const pageStore = usePageStore();
		await until(
			() =>
				document.readyState === "complete" &&
				Boolean(canvasStore.activeCanvas) &&
				!canvasStore.activeCanvas?.canvasProps.settingCanvas &&
				!pageStore.settingPage,
		).toBe(true);
		await document.fonts.ready;
		await nextFrame();
	}

	private applyView(view: CanvasView) {
		Object.assign(this.canvas.canvasProps, view);
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

	private fitView(scrollY: number): CanvasView {
		const container = this.canvasElement.closest(".canvas-container")!.getBoundingClientRect();
		const scale = Math.min(1, (container.width - FIT_PADDING * 2) / this.canvasElement.offsetWidth);
		const { top } = this.origin();
		return { scale, translateX: 0, translateY: (container.top + FIT_PADDING - top) / scale - scrollY };
	}

	// the inverse of fitView, so opening and closing straight away lands where it started
	private scrollYAtFitTop() {
		const container = this.canvasElement.closest(".canvas-container")!.getBoundingClientRect();
		const { scale, translateY } = this.canvas.canvasProps;
		return Math.max(0, Math.round((container.top + FIT_PADDING - this.origin().top) / scale - translateY));
	}

	private slidePanels(direction: "in" | "out", duration: number) {
		Object.entries(PANEL_OFFSCREEN).forEach(([panel, offscreen]) => {
			const element = getPanel(panel);
			if (!element) return;
			const onscreen = "none";
			element.style.transform = direction === "in" ? "" : offscreen;
			element.animate(
				direction === "in"
					? [{ transform: offscreen }, { transform: onscreen }]
					: [{ transform: onscreen }, { transform: offscreen }],
				{
					duration,
					delay: direction === "in" ? motion(80) : 0,
					easing: direction === "in" ? EASE_OUT : EASE_IN_OUT,
					fill: "backwards",
				},
			);
		});
	}
}

function getPanel(panel: string) {
	return document.querySelector<HTMLElement>(`[data-panel="${panel}"]`);
}

// the canvas copy of the link the visitor clicked, nearest to where they clicked it
function findAnchor(target: Rect) {
	const distance = (rect: DOMRect) => Math.hypot(rect.left - target.left, rect.top - target.top);
	return Array.from(
		document.querySelectorAll<HTMLElement>(".canvas [href='#editor-demo'], .canvas [data-editor-demo]"),
	)
		.map((element) => element.closest<HTMLElement>("[data-block-id]"))
		.filter((element): element is HTMLElement => Boolean(element))
		.sort((a, b) => distance(a.getBoundingClientRect()) - distance(b.getBoundingClientRect()))[0];
}

// a page whose images are still streaming in would give the hand-off away
function imagesInView() {
	const images = Array.from(document.querySelectorAll<HTMLImageElement>(".canvas img")).filter((image) => {
		const rect = image.getBoundingClientRect();
		return !image.complete && rect.bottom > 0 && rect.top < window.innerHeight;
	});
	return Promise.race([Promise.allSettled(images.map((image) => image.decode())), wait(1200)]);
}

export const editorDemoStage = new EditorDemoStage();
