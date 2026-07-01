import { nextTick, onScopeDispose, reactive, watch, watchEffect } from "vue";
import { addPxToNumber } from "./helpers";
import { getElementRectInEditor } from "./canvasFrameDom";

function trackTarget(target: HTMLElement | SVGElement, host: HTMLElement, canvasProps: CanvasProps) {
	const targetBounds = reactive({
		width: 0,
		height: 0,
		top: 0,
		left: 0,
		update() {
			const rect = getElementRectInEditor(target);
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

	watchEffect(() => {
		host.style.width = addPxToNumber(targetBounds.width, false);
		host.style.height = addPxToNumber(targetBounds.height, false);
		host.style.top = addPxToNumber(targetBounds.top, false);
		host.style.left = addPxToNumber(targetBounds.left, false);
	});

	onScopeDispose(() => {
		observer.disconnect();
		resizeObserver.disconnect();
	});

	return targetBounds.update;
}

export default trackTarget;
