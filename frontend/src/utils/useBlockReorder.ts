import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import {
	collectChildRects,
	computeDropIndex,
	computeIndicator,
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

// Pointer-based on-canvas reorder. The dragged block is lifted out of the flow
// (a floating ghost follows the cursor) and a real, same-sized placeholder is
// inserted into the target container — so the browser's own flex/grid engine
// positions the drop slot EXACTLY where the block will land (respecting
// display / justify-content / align-items / gap), and siblings open up to make
// room. The tree is only mutated on release, in one history entry.
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
	// the block's own container — reordering here shifts siblings (a real slot),
	// dropping into any OTHER container just shows a no-reflow line indicator
	const originalParentId = block.getParentBlock()?.blockId ?? null;

	let started = false;
	let ghost: HTMLElement | null = null;
	let placeholder: HTMLElement | null = null;
	let pauseId: unknown = null;
	let prevBodyCursor = "";
	let prevSourceDisplay = "";

	// resolved drop target at release time
	let dropParent: Block | null = null;
	let dropIndex: number | null = null;

	// A transparent spacer that occupies the dragged block's box (size + margins +
	// cross-axis alignment) so the flex layout reserves the real slot. The visible
	// indicator is drawn crisply as an overlay on top of this (see DropIndicator).
	const buildPlaceholder = (): HTMLElement => {
		const el = document.createElement("div");
		el.className = "reorder-placeholder";
		const cs = getComputedStyle(sourceEl);
		Object.assign(el.style, {
			boxSizing: "border-box",
			// offsetWidth/Height are unscaled border-box px (the placeholder lives
			// inside the scaled canvas, so it must use design-space sizes)
			width: `${sourceEl.offsetWidth}px`,
			height: `${sourceEl.offsetHeight}px`,
			marginTop: cs.marginTop,
			marginRight: cs.marginRight,
			marginBottom: cs.marginBottom,
			marginLeft: cs.marginLeft,
			alignSelf: cs.alignSelf,
			flex: "0 0 auto",
			pointerEvents: "none",
			background: "transparent",
		});
		return el;
	};

	const beginDrag = () => {
		started = true;
		canvasStore.isDragging = true;
		// suppress the click that fires after the drag so the block isn't
		// re-selected/toggled by useBlockEventHandlers
		canvasStore.preventClick = true;
		pauseId = canvasStore.activeCanvas?.history?.pause();

		const scale = getScale();
		// floating ghost — clone BEFORE hiding the source
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

		placeholder = buildPlaceholder();

		// lift the source out of the flow so its own slot closes up
		prevSourceDisplay = sourceEl.style.display;
		sourceEl.style.display = "none";

		prevBodyCursor = document.body.style.cursor;
		document.body.style.cursor = "grabbing";
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

	// An empty container is worth nesting into when it's clearly bigger than the
	// dragged block (a drop zone), not a same-sized leaf box you'd reorder past.
	const NEST_SIZE_FACTOR = 1.6;
	const isSpaciousContainer = (rawEl: HTMLElement): boolean => {
		const r = rawEl.getBoundingClientRect();
		return r.width >= sourceRect.width * NEST_SIZE_FACTOR && r.height >= sourceRect.height * NEST_SIZE_FACTOR;
	};

	// Decide the container to drop into, from whatever is under the cursor:
	//  - cursor over a container's body (populated, or an empty drop-zone) → nest inside
	//  - cursor over a childless leaf box → reorder as its sibling
	//  - cursor in the gap between items → elementFromPoint returns the parent, so
	//    you reorder at that level. No edge bands: the live layout (placeholder in
	//    place) drives everything, which is what keeps the drop stable.
	// Returns the resolved block AND its element so the caller doesn't re-query.
	const resolveTargetContainer = (clientX: number, clientY: number) => {
		const el = document.elementFromPoint(clientX, clientY) as HTMLElement | null;
		const hovered = el?.closest(".__builder_component__") as HTMLElement | null;
		let raw: Block | null = (hovered?.dataset.blockId && findBlock(hovered.dataset.blockId)) || null;

		while (raw && isSelfOrInsideDragged(raw)) raw = raw.getParentBlock();
		if (!raw) return null;

		const rawEl = getContainerEl(raw);
		const nonDraggedChildren = raw.getChildren().filter((c) => c.blockId !== block.blockId);
		const canNest =
			raw.canHaveChildren() && !!rawEl && (nonDraggedChildren.length > 0 || isSpaciousContainer(rawEl));

		let container: Block | null = canNest ? raw : raw.getParentBlock() || raw;

		while (container && (!container.canHaveChildren() || isSelfOrInsideDragged(container))) {
			container = container.getParentBlock();
		}
		if (!container) return null;
		// reuse rawEl when we settled on `raw` itself, otherwise resolve the element
		const parentEl = container === raw ? rawEl : getContainerEl(container);
		if (!parentEl) return null;
		return { parent: container, parentEl };
	};

	// Direct block children of a container, excluding the placeholder and the
	// (hidden) source — i.e. the real siblings, in DOM order.
	const realChildren = (containerEl: HTMLElement): HTMLElement[] =>
		Array.from(containerEl.children).filter(
			(c) => c !== placeholder && c !== sourceEl,
		) as HTMLElement[];

	const positionPlaceholder = (containerEl: HTMLElement, index: number) => {
		if (!placeholder) return;
		const ref = realChildren(containerEl)[index] || null;
		if (placeholder.parentElement !== containerEl || placeholder.nextElementSibling !== ref) {
			containerEl.insertBefore(placeholder, ref);
		}
	};

	const clearTarget = () => {
		dropParent = null;
		dropIndex = null;
		if (placeholder?.parentElement) placeholder.remove();
		canvasStore.clearReorderTarget();
	};

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
		const cr = parentEl.getBoundingClientRect();
		const t = canvasStore.reorderTarget;
		t.active = true;
		t.isComponentParent = parent.isExtendedFromComponent();
		t.containerRect = { top: cr.top, left: cr.left, width: cr.width, height: cr.height };
		dropParent = parent;

		if (parent.blockId === originalParentId) {
			// SAME container → real in-flow slot: the placeholder shifts siblings so
			// the drop position is exact. Index from the live layout (placeholder
			// excluded by class, hidden source by zero rect).
			const rects = collectChildRects(parentEl, direction, sourceEl);
			const index = computeDropIndex(rects, pointerMain);
			positionPlaceholder(parentEl, index);
			dropIndex = index;

			const pr = (placeholder as HTMLElement).getBoundingClientRect();
			t.mode = "slot";
			t.slotRect = { top: pr.top, left: pr.left, width: pr.width, height: pr.height };
			t.line = null;

			const gap = parseFloat(direction === "row" ? style.columnGap : style.rowGap) || 0;
			t.spacing = gap > 0 ? { value: Math.round(gap), left: pr.left + pr.width / 2, top: pr.top } : null;
		} else {
			// CROSS container → no layout shift: keep the placeholder out and show a
			// line indicator between the target's existing children. Computed from
			// the untouched layout, so there's no reflow feedback / jitter.
			if (placeholder?.parentElement) placeholder.remove();
			const rects = collectChildRects(parentEl, direction);
			const index = computeDropIndex(rects, pointerMain);
			dropIndex = index;

			t.mode = "line";
			t.slotRect = null;
			t.line = computeIndicator(rects, index, cr, style, direction);
			t.spacing = null;
		}
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
			// moveChild removes then inserts, so dropIndex (position among the
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
		if (placeholder?.parentElement) placeholder.remove();
		placeholder = null;

		if (started) {
			sourceEl.style.display = prevSourceDisplay;
			document.body.style.cursor = prevBodyCursor;
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
			// remove the placeholder before mutating the tree so Vue's re-render of
			// the container children isn't fighting a stray DOM node
			if (placeholder?.parentElement) placeholder.remove();
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
