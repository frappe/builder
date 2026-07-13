import { useElementBounding } from "@vueuse/core";
import { nextTick, onScopeDispose, reactive, watch, watchEffect } from "vue";
import { addPxToNumber } from "./helpers";

// All tracked targets share one MutationObserver on the canvas container. It is
// created when the first target registers and disconnected once the last one is
// removed, so it survives individual BlockEditor remounts (a component-scoped
// observer would die with whichever editor happened to create it) without leaking
// stale updaters across the session.
const updateList = new Set<() => void>();
let observer: MutationObserver | null = null;

function startObserver(container: HTMLElement) {
	observer = new MutationObserver(() => {
		nextTick(() => updateList.forEach((fn) => fn()));
	});
	observer.observe(container, {
		attributes: true,
		childList: true,
		subtree: true,
		attributeFilter: ["style", "class"],
		characterData: true,
	});
}

function trackTarget(target: HTMLElement | SVGElement, host: HTMLElement, canvasProps: CanvasProps) {
	const targetBounds = reactive(useElementBounding(target));
	const container = target.closest(".canvas-container") as HTMLElement | null;

	updateList.add(targetBounds.update);
	if (container && !observer) {
		startObserver(container);
	}

	watch(canvasProps, () => nextTick(targetBounds.update), { deep: true });

	// `targetBounds` is the axis-aligned box enclosing the rotated element, so it can't be
	// used directly for a rotated element: rotate the host around the same center instead,
	// sized to the target's own (unrotated) box, so it overlaps the element exactly.
	watchEffect(() => {
		const computedRotation = getComputedStyle(target as Element).rotate;
		const angle = computedRotation && computedRotation !== "none" ? parseFloat(computedRotation) || 0 : 0;
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
		if (updateList.size === 0 && observer) {
			observer.disconnect();
			observer = null;
		}
	});

	return targetBounds.update;
}

export default trackTarget;
