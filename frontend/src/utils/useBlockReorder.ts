import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import {
	clusterLines,
	collectChildRects,
	computeDropIndicator,
	computeReadingOrderIndex,
	getLayoutDirection,
} from "@/utils/dropGeometry";

const DRAG_THRESHOLD = 4; // px before a mousedown becomes a drag
const GHOST_OPACITY = 0.9;

// Can this block be reordered by dragging it on the canvas? (in-flow, not root,
// not an absolutely-positioned block — those free-move — and not owned by a
// component instance).
export function isReorderable(block: Block): boolean {
	return (
		!block.isRoot() &&
		!block.isMovable() &&
		!block.isChildOfComponent &&
		Boolean(block.getParentBlock())
	);
}

// Pointer-based on-canvas reorder, designed for zero layout jitter.
//
// The whole point: the canvas DOM is NEVER mutated while dragging. On pickup the
// source is lifted out of the flow exactly once (a single, clean reflow — the
// siblings close the gap) and a floating ghost follows the cursor. From then on
// every pointer move only MEASURES the target container's children (read-only)
// and repositions a fixed overlay line — no insertions, no per-move reflow, so
// there's nothing to jitter. The insertion index is computed in 2D reading
// order, so flex rows, flex columns, wrapped flex and CSS grid are all handled
// by the same code. The block tree is mutated once, on release, in one history
// entry.
export function startBlockReorder(event: MouseEvent, block: Block) {
	const canvasStore = useCanvasStore();
	const findBlock = (id: string): Block | null => canvasStore.activeCanvas?.findBlock(id) ?? null;
	const getScale = () => canvasStore.activeCanvas?.canvasProps?.scale || 1;

	const activeBreakpoint =
		canvasStore.activeCanvas?.activeBreakpoint || canvasStore.activeCanvas?.hoveredBreakpoint || "desktop";

	const getContainerEl = (target: Block): HTMLElement | null =>
		document.querySelector(
			`.__builder_component__[data-block-id="${target.blockId}"][data-breakpoint="${activeBreakpoint}"]`,
		) as HTMLElement | null;

	const sourceEl = getContainerEl(block);
	if (!sourceEl) return;

	const startX = event.clientX;
	const startY = event.clientY;
	const sourceRect = sourceEl.getBoundingClientRect();
	const grabOffsetX = startX - sourceRect.left;
	const grabOffsetY = startY - sourceRect.top;
	// the block's own container — dropping here reorders (same parent); dropping
	// into any other container moves the block across
	const originalParentId = block.getParentBlock()?.blockId ?? null;

	let started = false;
	let ghost: HTMLElement | null = null;
	let pauseId: unknown = null;
	let prevSourceVisibility = "";

	// resolved drop target at release time
	let dropParent: Block | null = null;
	let dropIndex: number | null = null;

	const beginDrag = () => {
		started = true;
		canvasStore.isDragging = true;
		// selecting on grab means point-drag doubles as selection — no need to
		// click-to-select first. preventClick stops the trailing click from
		// toggling the selection back off.
		canvasStore.selectBlock(block, null);
		canvasStore.preventClick = true;
		pauseId = canvasStore.activeCanvas?.history?.pause();

		const scale = getScale();
		// floating ghost — clone BEFORE dimming the source
		ghost = document.createElement("div");
		ghost.id = "reorder-ghost";
		const clone = sourceEl.cloneNode(true) as HTMLElement;
		clone.style.margin = "0";
		ghost.appendChild(clone);
		Object.assign(ghost.style, {
			position: "fixed",
			left: "0",
			top: "0",
			width: `${sourceRect.width / scale}px`,
			height: `${sourceRect.height / scale}px`,
			transformOrigin: "top left",
			transform: `translate(${sourceRect.left}px, ${sourceRect.top}px) scale(${scale})`,
			opacity: String(GHOST_OPACITY),
			pointerEvents: "none",
			zIndex: "999999",
			boxShadow: "0 12px 32px rgba(0,0,0,0.24), 0 2px 6px rgba(0,0,0,0.12)",
			borderRadius: "6px",
			overflow: "hidden",
			willChange: "transform",
		});
		document.body.appendChild(ghost);

		// Hide the source WITHOUT removing it from the flow (visibility, not
		// display) so it keeps its slot. Nothing shifts on pickup — critical for
		// grids, where display:none would renumber every following cell — and since
		// visibility:hidden elements are skipped by elementFromPoint and excluded
		// from measurement, the layout is completely frozen for the whole drag.
		prevSourceVisibility = sourceEl.style.visibility;
		sourceEl.style.visibility = "hidden";
	};

	// Is `candidate` the dragged block itself, or somewhere inside its subtree?
	const isSelfOrInsideDragged = (candidate: Block): boolean => {
		let node: Block | null = candidate;
		while (node) {
			if (node.blockId === block.blockId) return true;
			node = node.getParentBlock();
		}
		return false;
	};

	// Fraction of a container-child's main-axis extent, at EACH end, reserved for
	// "reorder beside me" instead of "nest inside me". Without this you could only
	// reorder past a child container by hitting the hairline gap/edge between
	// siblings — impossible when they're flush. 0.3 → the outer 30% on each side
	// reorders (so ~60% of a flush row is reorderable), the inner 40% nests.
	const EDGE_REORDER_BAND = 0.3;
	// EMPTY child containers default to before/after (you usually want to add a
	// sibling next to an existing child, not drop inside it) — nesting is reserved
	// for a small dead-centre core. Populated containers keep the normal band.
	const EDGE_REORDER_BAND_EMPTY = 0.42;

	// Is the pointer in `childEl`'s outer edge band (NOT its inner core), measured
	// along its parent's layout axis? In the edge band = "reorder beside this
	// container"; in the core = "nest into it".
	const inEdgeBand = (
		childEl: HTMLElement,
		parentBlock: Block,
		clientX: number,
		clientY: number,
		bandFraction: number,
	): boolean => {
		const parentEl = getContainerEl(parentBlock);
		const dir = parentEl ? getLayoutDirection(getComputedStyle(parentEl)) : "column";
		const r = childEl.getBoundingClientRect();
		const lo = dir === "row" ? r.left : r.top;
		const hi = dir === "row" ? r.right : r.bottom;
		const pointer = dir === "row" ? clientX : clientY;
		const band = (hi - lo) * bandFraction;
		return pointer < lo + band || pointer > hi - band;
	};

	// Auto-detect intent from whatever is under the cursor, no modifier keys.
	// Decided from the DEEPEST hovered block only (single level — deeper climbing
	// wrongly pops out of tall containers like a grid's lower row):
	//  - a childless leaf → reorder among its siblings (in its parent)
	//  - a container hovered on its INNER CORE → nest inside it
	//  - a container hovered on its outer EDGE BAND → reorder beside it in its parent
	//    (this is what makes a flush row/column of containers reorderable without a
	//    gap to aim at)
	//  - a gap between items → elementFromPoint already returns the parent
	// Returns the resolved block AND its element so the caller doesn't re-query.
	const resolveTargetContainer = (clientX: number, clientY: number) => {
		const el = document.elementFromPoint(clientX, clientY) as HTMLElement | null;
		const hovered = el?.closest(".__builder_component__") as HTMLElement | null;
		let raw: Block | null = (hovered?.dataset.blockId && findBlock(hovered.dataset.blockId)) || null;

		while (raw && isSelfOrInsideDragged(raw)) raw = raw.getParentBlock();
		if (!raw) return null;

		const rawEl = getContainerEl(raw);
		const nonDragged = raw.getChildren().filter((c) => c.blockId !== block.blockId);
		// Dropping back into the source's OWN parent when the source is its only
		// child is a no-op — so never nest there; fall through to before/after it.
		// This is what lets you drag a deeply-nested block OUT: hovering the (now
		// apparently empty) parent it came from resolves to its grandparent.
		const isEmptySourceParent = raw.blockId === originalParentId && nonDragged.length === 0;
		// Any container that can hold children is a nest target — including one the
		// same size as (or smaller than) the dragged block. The edge band below is
		// what separates nest (dead-centre) from reorder-beside (edges), so no size
		// heuristic is needed; empty containers just get a wider band (mostly
		// before/after, centre nests).
		let canNest = !isEmptySourceParent && raw.canHaveChildren() && !!rawEl;

		// Over a nestable container's outer edge band → reorder BESIDE it in its
		// parent instead of nesting. Empty containers get a wider band so they
		// default to before/after (add a sibling) rather than nest-inside.
		const parent = raw.getParentBlock();
		if (canNest && rawEl && parent) {
			const band = nonDragged.length === 0 ? EDGE_REORDER_BAND_EMPTY : EDGE_REORDER_BAND;
			if (inEdgeBand(rawEl, parent, clientX, clientY, band)) canNest = false;
		}

		let container: Block | null = canNest ? raw : parent || raw;

		while (container && (!container.canHaveChildren() || isSelfOrInsideDragged(container))) {
			container = container.getParentBlock();
		}
		if (!container) return null;
		const parentEl = container === raw ? rawEl : getContainerEl(container);
		if (!parentEl) return null;
		return { parent: container, parentEl };
	};

	const clearTarget = () => {
		dropParent = null;
		dropIndex = null;
		canvasStore.clearReorderTarget();
	};

	// Read-only: measure the resolved container's children and update the overlay.
	// No DOM writes → no reflow → no jitter.
	const updateTarget = (clientX: number, clientY: number) => {
		const resolved = resolveTargetContainer(clientX, clientY);
		if (!resolved) {
			clearTarget();
			return;
		}
		const { parent, parentEl } = resolved;

		const style = getComputedStyle(parentEl);
		const direction = getLayoutDirection(style);
		const pointerMain = direction === "row" ? clientX : clientY;
		const pointerCross = direction === "row" ? clientY : clientX;

		const rects = collectChildRects(parentEl, direction, sourceEl);
		const lines = clusterLines(rects);
		const index = computeReadingOrderIndex(lines, pointerMain, pointerCross);

		const cr = parentEl.getBoundingClientRect();
		dropParent = parent;
		dropIndex = index;

		const t = canvasStore.reorderTarget;
		t.active = true;
		t.isComponentParent = parent.isExtendedFromComponent();
		t.isSameContainer = parent.blockId === originalParentId;
		t.containerRect = { top: cr.top, left: cr.left, width: cr.width, height: cr.height };
		t.line = computeDropIndicator(lines, index, cr, style, direction, {
			width: sourceRect.width,
			height: sourceRect.height,
		});
	};

	const positionGhost = (clientX: number, clientY: number) => {
		if (!ghost) return;
		ghost.style.transform = `translate(${clientX - grabOffsetX}px, ${clientY - grabOffsetY}px) scale(${getScale()})`;
	};

	const commit = () => {
		if (dropParent === null || dropIndex === null) return;
		const oldParent = block.getParentBlock();
		if (!oldParent) return;

		if (dropParent.blockId === oldParent.blockId) {
			// moveChild removes then re-inserts, so dropIndex (position among the
			// non-dragged siblings) maps directly.
			oldParent.moveChild(block, dropIndex);
		} else {
			oldParent.removeChild(block);
			dropParent.addChild(block, dropIndex, false);
		}
		canvasStore.selectBlock(block, null);
	};

	const cleanup = () => {
		document.removeEventListener("mousemove", onMove);
		document.removeEventListener("mouseup", onUp);
		document.removeEventListener("keydown", onKey);

		if (ghost) ghost.remove();
		ghost = null;

		if (started) {
			sourceEl.style.visibility = prevSourceVisibility;
			canvasStore.isDragging = false;
		}
		canvasStore.clearReorderTarget();

		if (pauseId) {
			// Resume WITHOUT committing: the tree mutation in commit() runs in this
			// same mouseup tick, so its deep-watch flush is still pending and the
			// natural (debounced) watcher records exactly one history entry once
			// unpaused. Passing commitNow here would double it. A no-op drag leaves
			// the tree unchanged, so the watcher records nothing.
			canvasStore.activeCanvas?.history?.resume(pauseId as never, false);
			pauseId = null;
		}
	};

	const onMove = (e: MouseEvent) => {
		if (!started) {
			if (Math.abs(e.clientX - startX) < DRAG_THRESHOLD && Math.abs(e.clientY - startY) < DRAG_THRESHOLD) {
				return;
			}
			beginDrag();
		}
		e.preventDefault();
		positionGhost(e.clientX, e.clientY);
		updateTarget(e.clientX, e.clientY);
	};

	const onUp = () => {
		if (started && dropParent !== null && dropIndex !== null) {
			commit();
		}
		cleanup();
	};

	const onKey = (e: KeyboardEvent) => {
		if (e.key === "Escape") {
			dropParent = null;
			dropIndex = null;
			cleanup();
		}
	};

	document.addEventListener("mousemove", onMove);
	document.addEventListener("mouseup", onUp);
	document.addEventListener("keydown", onKey);
}
