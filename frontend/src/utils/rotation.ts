import type Block from "@/block";

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

// Converts screen-space movement to the element's local axes.
function toLocalDelta(dx: number, dy: number, rotationDeg: number) {
	const rad = (rotationDeg * Math.PI) / 180;
	const cos = Math.cos(rad);
	const sin = Math.sin(rad);
	return {
		x: dx * cos + dy * sin,
		y: dy * cos - dx * sin,
	};
}

// Uses the reactive block style so computed cursors update with style-panel edits.
function getTotalRotation(target: Element, targetBlock: Block): number {
	const ownRotation = parseFloat(String(targetBlock.getStyle("rotate") || 0)) || 0;
	return ownRotation + getElementRotation(target.parentElement);
}

export { getElementRotation, getTotalRotation, toLocalDelta };
