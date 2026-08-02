import { useElementBounding } from "@vueuse/core";
import { nextTick, onScopeDispose, reactive, watch, watchEffect } from "vue";
import { closestAcrossShadow } from "./canvasShadowDom";
import { getElementRotation } from "./rotation";
import { addPxToNumber } from "./helpers";

// All tracked targets share one MutationObserver on the canvas container. It is
// created when the first target registers and disconnected once the last one is
// removed, so it survives individual BlockEditor remounts (a component-scoped
// observer would die with whichever editor happened to create it) without leaking
// stale updaters across the session.
const updateList = new Set<() => void>();
const observedRoots = new Set<Node>();
let observer: MutationObserver | null = null;

const OBSERVER_OPTIONS = {
	attributes: true,
	childList: true,
	subtree: true,
	attributeFilter: ["style", "class"],
	characterData: true,
};

// One observer watches several roots. subtree does not reach into a shadow tree,
// so it must observe each canvas shadow root on its own.
function observeRoot(root: Node) {
	if (!observer) {
		observer = new MutationObserver(() => {
			nextTick(() => updateList.forEach((fn) => fn()));
		});
	}
	if (observedRoots.has(root)) return;
	observedRoots.add(root);
	observer.observe(root, OBSERVER_OPTIONS);
}

function stopObserver() {
	observer?.disconnect();
	observer = null;
	observedRoots.clear();
}

function trackTarget(target: HTMLElement | SVGElement, host: HTMLElement, canvasProps: CanvasProps) {
	const targetBounds = reactive(useElementBounding(target));
	// the target renders in a shadow root, so closest() alone stops at the boundary
	// and the observer never starts
	const container = closestAcrossShadow(target, ".canvas-container");

	updateList.add(targetBounds.update);
	if (container) observeRoot(container);
	const targetRoot = target.getRootNode();
	if (targetRoot instanceof ShadowRoot) observeRoot(targetRoot);

	watch(canvasProps, () => nextTick(targetBounds.update), { deep: true });

	// `targetBounds` is the axis-aligned box enclosing the rotated element, so it can't be
	// used directly for a rotated element: rotate the host around the same center instead,
	// sized to the target's own (unrotated) box, so it overlaps the element exactly.
	watchEffect(() => {
		const angle = getElementRotation(target as Element);
		if (angle) {
			const scale = canvasProps.scale;
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
		updateList.delete(targetBounds.update);
		if (updateList.size === 0) stopObserver();
	});

	return targetBounds.update;
}

export default trackTarget;
