import { nextTick, onScopeDispose, reactive, watch, watchEffect } from "vue";
import { getElementRotation } from "./rotation";
import { addPxToNumber } from "./helpers";
import { getElementRectInEditor } from "./canvasFrameDom";

function trackTarget(target: HTMLElement | SVGElement, host: HTMLElement, canvasProps: CanvasProps) {
	// an editor hosted in the same canvas frame as its target is already scaled by the canvas
	const inTargetDocument = target.ownerDocument === host.ownerDocument;
	const targetBounds = reactive({
		width: 0,
		height: 0,
		top: 0,
		left: 0,
		update() {
			const rect = inTargetDocument ? target.getBoundingClientRect() : getElementRectInEditor(target);
			targetBounds.width = rect.width;
			targetBounds.height = rect.height;
			targetBounds.top = rect.top;
			targetBounds.left = rect.left;
		},
	});
	const observer = new MutationObserver(() => nextTick(targetBounds.update));
	observer.observe(target.ownerDocument.body, {
		attributes: true,
		childList: true,
		subtree: true,
		attributeFilter: ["style", "class"],
		characterData: true,
	});
	const resizeObserver = new ResizeObserver(() => targetBounds.update());
	resizeObserver.observe(target);
	targetBounds.update();

	watch(canvasProps, () => nextTick(targetBounds.update), { deep: true });

	// `targetBounds` is the axis-aligned box enclosing the rotated element, so it can't be
	// used directly for a rotated element: rotate the host around the same center instead,
	// sized to the target's own (unrotated) box, so it overlaps the element exactly.
	watchEffect(() => {
		const angle = getElementRotation(target as Element);
		if (angle) {
			const scale = inTargetDocument ? 1 : canvasProps.scale;
			const width = (target as HTMLElement).offsetWidth * scale;
			const height = (target as HTMLElement).offsetHeight * scale;
			const centerX = targetBounds.left + targetBounds.width / 2;
			const centerY = targetBounds.top + targetBounds.height / 2;
			host.style.rotate = `${angle}deg`;
			host.style.width = addPxToNumber(width, false);
			host.style.height = addPxToNumber(height, false);
			host.style.left = addPxToNumber(centerX - width / 2, false);
			host.style.top = addPxToNumber(centerY - height / 2, false);
		} else {
			host.style.rotate = "";
			host.style.width = addPxToNumber(targetBounds.width, false);
			host.style.height = addPxToNumber(targetBounds.height, false);
			host.style.top = addPxToNumber(targetBounds.top, false);
			host.style.left = addPxToNumber(targetBounds.left, false);
		}
	});

	onScopeDispose(() => {
		observer.disconnect();
		resizeObserver.disconnect();
	});

	return targetBounds.update;
}

export default trackTarget;
