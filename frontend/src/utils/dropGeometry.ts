// Layout-aware drop geometry shared by the on-canvas reorder engine and the
// panel drop zone. All coordinates are in client (screen) space so callers can
// position fixed overlays directly and mix live getBoundingClientRect values
// with cursor clientX/clientY without worrying about canvas scale/translate.
//
// The reorder engine never mutates the canvas DOM while dragging — it measures
// the (static) children once per pointer move and draws an overlay indicator.
// So everything here is pure geometry: it takes rects + a pointer and returns
// an insertion index / an indicator line, and is fully layout-aware (flex row,
// flex column, wrapped flex, and CSS grid all fall out of the same 2D model).

export type LayoutDirection = "row" | "column";
export type IndicatorOrientation = "vertical" | "horizontal";

export interface ChildRect {
	// main-axis extents (left/right for row, top/bottom for column)
	start: number;
	end: number;
	mid: number;
	// cross-axis extents (used to cluster into rows and to size the line)
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
		return style.gridAutoFlow.includes("column") ? "column" : "row";
	}
	// block-level and inline children stack vertically
	return "column";
}

// Snapshot the direct block children of a container along the given axis.
// `excludeEl` (the block currently being dragged) is skipped so its own slot
// doesn't influence the computed index. Returned in DOM order, which — for
// every layout the builder produces — matches visual reading order.
export function collectChildRects(
	parentEl: HTMLElement,
	direction: LayoutDirection,
	excludeEl?: HTMLElement | null,
): ChildRect[] {
	const children = Array.from(parentEl.querySelectorAll(`:scope > ${BUILDER_SELECTOR}`)) as HTMLElement[];

	const rects: ChildRect[] = [];
	for (const el of children) {
		// Skip only the dragged element itself — NOT an ancestor-path child that
		// merely contains it. When you drag a deeply-nested block out to one of its
		// ancestors, the child on the path to the source is a real sibling target
		// (you want to drop before/after it), so it must stay counted.
		if (excludeEl && el === excludeEl) continue;
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
	return rects;
}

// Two rects share a visual line when they overlap on the cross axis by more than
// half of the smaller one — robust to ragged item heights in a grid row.
function sameLine(a: ChildRect, b: ChildRect): boolean {
	const overlap = Math.min(a.crossEnd, b.crossEnd) - Math.max(a.crossStart, b.crossStart);
	const minSize = Math.min(a.crossEnd - a.crossStart, b.crossEnd - b.crossStart) || 1;
	return overlap > minSize * 0.5;
}

// Group children into visual lines (grid rows for a row layout, the single
// stacked column for a column/flex layout) in reading order. A one-line result
// means a plain flex row/column; multiple lines means a wrapped flex or a grid.
// Because DOM order is reading order, a new line simply starts whenever the next
// child no longer overlaps the current line's cross band.
export function clusterLines(rects: ChildRect[]): ChildRect[][] {
	const lines: ChildRect[][] = [];
	let current: ChildRect[] = [];
	for (const r of rects) {
		const onCurrent = current.length > 0 && current.some((c) => sameLine(c, r));
		if (!onCurrent && current.length) {
			lines.push(current);
			current = [];
		}
		current.push(r);
	}
	if (current.length) lines.push(current);
	// order items within each line by their main-axis start (usually already so)
	for (const line of lines) line.sort((a, b) => a.start - b.start);
	return lines;
}

function lineBand(line: ChildRect[]): { start: number; end: number } {
	return {
		start: Math.min(...line.map((r) => r.crossStart)),
		end: Math.max(...line.map((r) => r.crossEnd)),
	};
}

// 2D reading-order insertion index: how many children come before the pointer,
// scanning line-by-line down the cross axis and item-by-item along the main
// axis. Reduces to a simple midpoint scan for a single flex line, and handles
// wrapped flex / grid without any special-casing. Monotonic within a line (the
// index only changes when the pointer crosses an item midpoint or a line
// boundary), so there's no oscillation at the edges.
export function computeReadingOrderIndex(
	lines: ChildRect[][],
	pointerMain: number,
	pointerCross: number,
): number {
	let index = 0;
	for (const line of lines) {
		const band = lineBand(line);
		if (pointerCross > band.end) {
			// the whole line sits above the pointer → it's entirely before it
			index += line.length;
			continue;
		}
		if (pointerCross < band.start) {
			// this line (and every later one) is below the pointer → stop
			break;
		}
		// pointer is within this line's band → count items to its left
		for (const item of line) {
			if (pointerMain > item.mid) index++;
			else break;
		}
		return index;
	}
	return index;
}

// Where to draw the insertion line for a resolved index. Uses the two children
// bracketing the insertion point:
//   - both present and on the same line → centre the line in the gap between
//     them, spanning their shared cross band (the clean flex-row/column look)
//   - only a following child (line start, or the very first slot) → a caret at
//     its leading edge, spanning that cell — reads as "insert before this cell",
//     which is what makes grid drops legible
//   - only a preceding child (very last slot) → a caret at its trailing edge
//   - no children (empty container) → place it where the first child will land,
//     honouring the container's justify-content (main axis) and align-items
//     (cross axis), sized to the dragged block when known
// The caller passes the container's measured rect + computed style so the drag
// hot path doesn't re-measure them. `sourceSize` (the dragged block's screen-px
// box) lets the empty-container indicator match the incoming block's extent.
export function computeDropIndicator(
	lines: ChildRect[][],
	index: number,
	parentRect: DOMRect,
	style: CSSStyleDeclaration,
	direction: LayoutDirection,
	sourceSize?: { width: number; height: number },
): IndicatorGeometry {
	const orientation: IndicatorOrientation = direction === "row" ? "vertical" : "horizontal";
	const flat = lines.flat();

	const build = (mainPos: number, crossStart: number, crossEnd: number): IndicatorGeometry => {
		const length = Math.max(crossEnd - crossStart, 4);
		return orientation === "vertical"
			? { orientation, left: mainPos, top: crossStart, length }
			: { orientation, left: crossStart, top: mainPos, length };
	};

	if (flat.length === 0) {
		const padTop = parseFloat(style.paddingTop) || 0;
		const padBottom = parseFloat(style.paddingBottom) || 0;
		const padLeft = parseFloat(style.paddingLeft) || 0;
		const padRight = parseFloat(style.paddingRight) || 0;
		// content-box extents along the main + cross axes
		const mainLo = direction === "row" ? parentRect.left + padLeft : parentRect.top + padTop;
		const mainHi = direction === "row" ? parentRect.right - padRight : parentRect.bottom - padBottom;
		const crossLo = direction === "row" ? parentRect.top + padTop : parentRect.left + padLeft;
		const crossHi = direction === "row" ? parentRect.bottom - padBottom : parentRect.right - padRight;

		// main-axis position of the line ← justify-content
		const justify = style.justifyContent;
		let mainPos: number;
		if (justify === "center" || justify === "space-around" || justify === "space-evenly") {
			mainPos = (mainLo + mainHi) / 2;
		} else if (justify === "flex-end" || justify === "end" || justify === "right") {
			mainPos = mainHi;
		} else {
			mainPos = mainLo;
		}

		// cross-axis span of the line ← align-items (sized to the dragged block)
		const align = style.alignItems;
		const sourceCross = sourceSize ? (direction === "row" ? sourceSize.height : sourceSize.width) : 0;
		let cs = crossLo;
		let ce = crossHi;
		if (sourceCross > 0 && align !== "stretch" && align !== "normal" && align !== "") {
			if (align === "center") {
				const c = (crossLo + crossHi) / 2;
				cs = c - sourceCross / 2;
				ce = c + sourceCross / 2;
			} else if (align === "flex-end" || align === "end") {
				cs = crossHi - sourceCross;
				ce = crossHi;
			} else {
				cs = crossLo;
				ce = crossLo + sourceCross;
			}
			cs = Math.max(cs, crossLo);
			ce = Math.min(ce, crossHi);
		}
		return build(mainPos, cs, ce);
	}

	const prev = index > 0 ? flat[index - 1] : null;
	const next = index < flat.length ? flat[index] : null;

	if (prev && next && sameLine(prev, next)) {
		const mid = (prev.end + next.start) / 2;
		return build(mid, Math.min(prev.crossStart, next.crossStart), Math.max(prev.crossEnd, next.crossEnd));
	}
	if (next) {
		return build(next.start, next.crossStart, next.crossEnd);
	}
	// prev is guaranteed here (flat.length > 0 and next is null)
	return build((prev as ChildRect).end, (prev as ChildRect).crossStart, (prev as ChildRect).crossEnd);
}
