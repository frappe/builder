import useBuilderStore from "@/stores/builderStore";
import type { CanvasProps } from "@/types/Builder/BuilderCanvas";
import { useEventListener } from "@vueuse/core";
import { onScopeDispose, type Ref, watch } from "vue";

const EDGE_MARGIN = 120;
const BLOCK_PADDING = 60;
const GLIDE_EASE = 0.25;

/**
 * Auto-pans the canvas to keep the AI's latest work in view while a build is
 * running. Pan only, never zoom. Any user camera move (wheel, grab-drag, zoom,
 * fit to screen) pauses following; it resumes when the user brings the follow
 * target back into view, or when a new build starts.
 */
export function useBuildFollow(
	canvasProps: CanvasProps,
	canvasContainer: Ref<HTMLElement | null>,
	canvas: Ref<HTMLElement | null>,
) {
	const builderStore = useBuilderStore();
	let userTookCamera = false;
	let frame = 0;
	let pendingX = 0;
	let pendingY = 0;
	let lastContentHeight = 0;
	const expected = { scale: 0, x: 0, y: 0 };

	// Streaming generation grows the page downward; keep the bottom edge in view.
	function followBuildEdge() {
		const rects = getRects();
		if (!rects) return;
		const { container, content } = rects;
		// The chunk landed before this runs, so a paused user who panned back to the
		// frontier already has it pushed below the viewport again. Judge visibility
		// by where the edge sat before this chunk's growth.
		const grownBy = Math.max(0, content.height - lastContentHeight);
		lastContentHeight = content.height;
		const edgeBefore = content.bottom - grownBy;
		const edgeVisible =
			(content.bottom >= container.top && content.bottom <= container.bottom) ||
			(edgeBefore >= container.top && edgeBefore <= container.bottom);
		if (!mayFollow(edgeVisible)) return;
		const margin = Math.min(EDGE_MARGIN, container.height * 0.2);
		const overflow = content.bottom - (container.bottom - margin);
		if (overflow > 0) retargetGlide(0, -overflow);
	}

	function followBlock(blockId: string) {
		const rects = getRects();
		const el = findBlockElement(blockId);
		if (!rects || !el) return;
		const { container } = rects;
		const rect = el.getBoundingClientRect();
		const inView =
			rect.top >= container.top &&
			rect.bottom <= container.bottom &&
			rect.left >= container.left &&
			rect.right <= container.right;
		if (!mayFollow(inView)) return;
		const dx = slideDelta(rect.left, rect.right, container.left, container.right);
		const dy = slideDelta(rect.top, rect.bottom, container.top, container.bottom);
		if (dx || dy) retargetGlide(dx, dy);
	}

	// A visible target means the user is already looking at the build; re-engage.
	function mayFollow(targetVisible: boolean) {
		if (userTookCamera && !targetVisible) return false;
		userTookCamera = false;
		return true;
	}

	function pause() {
		userTookCamera = true;
		stopGlide();
	}

	function getRects() {
		if (!canvasContainer.value || !canvas.value) return null;
		return {
			container: canvasContainer.value.getBoundingClientRect(),
			content: canvas.value.getBoundingClientRect(),
		};
	}

	function findBlockElement(blockId: string) {
		const candidates = canvasContainer.value?.querySelectorAll(`.canvas [data-block-id="${blockId}"]`);
		for (const el of candidates || []) {
			const rect = el.getBoundingClientRect();
			if (rect.width || rect.height) return el as HTMLElement;
		}
		return null;
	}

	// Screen-px shift that slides [start, end] inside the padded bounds.
	function slideDelta(start: number, end: number, boundStart: number, boundEnd: number) {
		const room = boundEnd - boundStart - BLOCK_PADDING * 2;
		if (end - start >= room) return boundStart + BLOCK_PADDING - start;
		if (start < boundStart + BLOCK_PADDING) return boundStart + BLOCK_PADDING - start;
		if (end > boundEnd - BLOCK_PADDING) return boundEnd - BLOCK_PADDING - end;
		return 0;
	}

	// Each call re-measures from the live DOM, so replace the remainder, never add.
	function retargetGlide(dx: number, dy: number) {
		pendingX = dx;
		pendingY = dy;
		if (!frame) frame = requestAnimationFrame(glideStep);
	}

	function glideStep() {
		const stepX = glideCut(pendingX);
		const stepY = glideCut(pendingY);
		applyPan(stepX, stepY);
		pendingX -= stepX;
		pendingY -= stepY;
		frame = pendingX || pendingY ? requestAnimationFrame(glideStep) : 0;
	}

	function glideCut(remaining: number) {
		return Math.abs(remaining) < 1 ? remaining : remaining * GLIDE_EASE;
	}

	function stopGlide() {
		if (frame) cancelAnimationFrame(frame);
		frame = 0;
		pendingX = 0;
		pendingY = 0;
	}

	function applyPan(dx: number, dy: number) {
		if (!dx && !dy) return;
		canvasProps.translateX += dx / canvasProps.scale;
		canvasProps.translateY += dy / canvasProps.scale;
		syncExpected();
	}

	function syncExpected() {
		expected.scale = canvasProps.scale;
		expected.x = canvasProps.translateX;
		expected.y = canvasProps.translateY;
	}

	syncExpected();
	onScopeDispose(stopGlide);

	// Explicit camera input, cheap to detect directly.
	useEventListener(canvasContainer, "wheel", pause, { capture: true, passive: true });
	useEventListener(canvasContainer, "mousedown", () => {
		if (builderStore.mode === "move") pause();
	});

	// Fallback for every other camera mover (zoom shortcuts, fit button, selection
	// scroll): a value we didn't write ourselves means someone took the camera.
	watch(
		() => [canvasProps.scale, canvasProps.translateX, canvasProps.translateY],
		([scale, x, y]) => {
			const ours =
				Math.abs(scale - expected.scale) < 0.001 &&
				Math.abs(x - expected.x) < 0.001 &&
				Math.abs(y - expected.y) < 0.001;
			if (!ours && !canvasProps.settingCanvas) pause();
			syncExpected();
		},
	);

	watch(
		() => builderStore.aiBuildingCanvas,
		(building) => {
			if (building) userTookCamera = false;
		},
	);

	return { followBuildEdge, followBlock };
}
