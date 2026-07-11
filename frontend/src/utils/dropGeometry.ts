// Layout-aware drop geometry shared by the on-canvas reorder engine and the
// panel drop zone. All coordinates are in client (screen) space so callers can
// position fixed overlays directly and mix live getBoundingClientRect values
// with cursor clientX/clientY without worrying about canvas scale/translate.

export type LayoutDirection = "row" | "column";
export type IndicatorOrientation = "vertical" | "horizontal";

export interface ChildRect {
	// main-axis extents (left/right for row, top/bottom for column)
	start: number;
	end: number;
	mid: number;
	// cross-axis extents (used to size the insertion line)
	crossStart: number;
	crossEnd: number;
}

export interface IndicatorGeometry {
	orientation: IndicatorOrientation;
	// top-left of the line in client coords + its length
	left: number;
	top: number;
	length: number;
}

const BUILDER_SELECTOR = ".__builder_component__";

export function getLayoutDirection(style: CSSStyleDeclaration): LayoutDirection {
	const display = style.display;
	if (display === "flex" || display === "inline-flex") {
		return style.flexDirection.includes("row") ? "row" : "column";
	} else if (display === "grid" || display === "inline-grid") {
		return style.gridAutoFlow.includes("row") ? "row" : "column";
	}
	// block-level and inline children stack vertically
	return "column";
}

// Snapshot the direct block children of a container along the given axis.
// `excludeEl` (the block currently being dragged) is skipped so its own slot
// doesn't influence the computed index.
export function collectChildRects(
	parentEl: HTMLElement,
	direction: LayoutDirection,
	excludeEl?: HTMLElement | null,
): ChildRect[] {
	const children = Array.from(
		parentEl.querySelectorAll(`:scope > ${BUILDER_SELECTOR}`),
	) as HTMLElement[];

	const rects: ChildRect[] = [];
	for (const el of children) {
		if (excludeEl && (el === excludeEl || el.contains(excludeEl))) continue;
		const rect = el.getBoundingClientRect();
		// ignore zero-size / detached nodes
		if (rect.width === 0 && rect.height === 0) continue;
		if (direction === "row") {
			rects.push({
				start: rect.left,
				end: rect.right,
				mid: rect.left + rect.width / 2,
				crossStart: rect.top,
				crossEnd: rect.bottom,
			});
		} else {
			rects.push({
				start: rect.top,
				end: rect.bottom,
				mid: rect.top + rect.height / 2,
				crossStart: rect.left,
				crossEnd: rect.right,
			});
		}
	}
	// keep DOM order == visual order for the monotonic index scan below
	return rects;
}

// Monotonic insertion index: number of children whose midpoint sits before the
// pointer along the main axis. Monotonic (vs. nearest-child + before/after)
// means the index only ever changes when the pointer actually crosses a
// midpoint, so there's no oscillation at boundaries.
export function computeDropIndex(rects: ChildRect[], pointerMain: number): number {
	let index = 0;
	for (const child of rects) {
		if (pointerMain > child.mid) {
			index++;
		} else {
			break;
		}
	}
	return index;
}

// Where to draw the insertion line, given the resolved index. Falls in the gap
// between child[index-1] and child[index]; clamps to the container's content
// box when dropping at the very start/end or into an empty container. The
// caller passes the container's already-measured rect and computed style so the
// drag hot path doesn't re-measure them.
export function computeIndicator(
	rects: ChildRect[],
	index: number,
	parentRect: DOMRect,
	style: CSSStyleDeclaration,
	direction: LayoutDirection,
): IndicatorGeometry {
	const padTop = parseFloat(style.paddingTop) || 0;
	const padBottom = parseFloat(style.paddingBottom) || 0;
	const padLeft = parseFloat(style.paddingLeft) || 0;
	const padRight = parseFloat(style.paddingRight) || 0;

	const orientation: IndicatorOrientation = direction === "row" ? "vertical" : "horizontal";

	// main-axis position of the line
	let mainPos: number;
	if (rects.length === 0) {
		mainPos =
			direction === "row" ? parentRect.left + padLeft : parentRect.top + padTop;
	} else if (index <= 0) {
		mainPos = rects[0].start;
	} else if (index >= rects.length) {
		mainPos = rects[rects.length - 1].end;
	} else {
		// centre of the gap between the two neighbours
		mainPos = (rects[index - 1].end + rects[index].start) / 2;
	}

	// cross-axis span of the line — hug the children's extent when present,
	// otherwise span the container's content box
	let crossStart: number;
	let crossEnd: number;
	if (rects.length === 0) {
		if (direction === "row") {
			crossStart = parentRect.top + padTop;
			crossEnd = parentRect.bottom - padBottom;
		} else {
			crossStart = parentRect.left + padLeft;
			crossEnd = parentRect.right - padRight;
		}
	} else {
		crossStart = Math.min(...rects.map((r) => r.crossStart));
		crossEnd = Math.max(...rects.map((r) => r.crossEnd));
	}
	const length = Math.max(crossEnd - crossStart, 4);

	if (orientation === "vertical") {
		return { orientation, left: mainPos, top: crossStart, length };
	}
	return { orientation, left: crossStart, top: mainPos, length };
}
