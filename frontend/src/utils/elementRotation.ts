import type Block from "@/block";

// An element's own `rotate` style only reflects what's set on itself, but a child of a
// rotated block is visually rotated too (CSS transforms compose down the tree). Anything
// that needs the element's actual *rendered* angle must sum its own rotation with every
// rotated ancestor's, up to the canvas boundary.
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
	console.log({ el, rotation });
	return rotation;
}

// Projects a screen-space mouse movement onto an element's own (unrotated) local axes, so
// a drag still moves along the right dimension (width/height, margin, padding...) when the
// element is rendered rotated on screen.
function toLocalDelta(dx: number, dy: number, rotationDeg: number) {
	const rad = (rotationDeg * Math.PI) / 180;
	const cos = Math.cos(rad);
	const sin = Math.sin(rad);
	return {
		x: dx * cos + dy * sin,
		y: dy * cos - dx * sin,
	};
}

// Same total as getElementRotation, but reads the target's own rotation from the (reactive)
// block style instead of the DOM. A plain getComputedStyle read has no Vue dependency to
// invalidate on, so a computed built on it alone never re-runs when the value is edited
// from the style panel/angle dial - only when a drag imperatively re-sets the cursor itself.
function getTotalRotation(target: Element, targetBlock: Block): number {
	const ownRotation = parseFloat(String(targetBlock.getStyle("rotate") || 0)) || 0;
	return ownRotation + getElementRotation(target.parentElement);
}

export { getElementRotation, getTotalRotation, toLocalDelta };
