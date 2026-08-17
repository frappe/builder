import type Block from "@/block";

type ResizeDirection = {
	horizontal?: "left" | "right";
	vertical?: "top" | "bottom";
};

// Sums rotation from this element through the canvas.
function getElementRotation(el: Element | null): number {
	let rotation = 0;
	let current = el;
	while (current && !current.classList.contains("canvas-container")) {
		const rotate = getComputedStyle(current).rotate;
		if (rotate && rotate !== "none") {
			rotation += parseFloat(rotate) || 0;
		}
		current = current.parentElement;
	}
	return rotation;
}

function rotateDelta(x: number, y: number, rotationDeg: number) {
	const rad = (rotationDeg * Math.PI) / 180;
	return {
		x: x * Math.cos(rad) - y * Math.sin(rad),
		y: x * Math.sin(rad) + y * Math.cos(rad),
	};
}

// Converts screen-space movement to the element's local axes.
function toLocalDelta(dx: number, dy: number, rotationDeg: number) {
	return rotateDelta(dx, dy, -rotationDeg);
}

// Uses the reactive block style so computed cursors update with style-panel edits.
function getTotalRotation(target: Element, targetBlock: Block): number {
	const ownRotation = parseFloat(String(targetBlock.getActiveStyleValue("rotate") || 0)) || 0;
	return ownRotation + getElementRotation(target.parentElement);
}

// Keeps the opposite local edge fixed as a center-rotated element changes size.
function getResizePositionDelta(
	widthMovement: number,
	heightMovement: number,
	{ horizontal, vertical }: ResizeDirection,
	rotationDeg: number,
) {
	const centerDelta = { x: widthMovement / 2, y: heightMovement / 2 };
	const oppositeEdgeDelta = {
		x: horizontal === "left" ? centerDelta.x : horizontal === "right" ? -centerDelta.x : 0,
		y: vertical === "top" ? centerDelta.y : vertical === "bottom" ? -centerDelta.y : 0,
	};
	const rotatedEdgeDelta = rotateDelta(oppositeEdgeDelta.x, oppositeEdgeDelta.y, rotationDeg);
	return {
		x: -centerDelta.x - rotatedEdgeDelta.x || 0,
		y: -centerDelta.y - rotatedEdgeDelta.y || 0,
	};
}

export { getElementRotation, getResizePositionDelta, getTotalRotation, toLocalDelta };
export type { ResizeDirection };
