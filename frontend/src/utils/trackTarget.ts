import { useElementBounding, useMutationObserver } from "@vueuse/core";
import { nextTick, reactive, watch, watchEffect } from "vue";
import { addPxToNumber } from "./helpers";

declare global {
	interface Window {
		observer: any;
	}
}

window.observer = null;
const updateList: (() => void)[] = [];

function trackTarget(target: HTMLElement | SVGElement, host: HTMLElement, canvasProps: CanvasProps) {
	const targetBounds = reactive(useElementBounding(target));
	const container = target.closest(".canvas-container");
	// TODO: too much? find a better way to track changes
	updateList.push(targetBounds.update);
	watch(canvasProps, () => nextTick(targetBounds.update), { deep: true });

	if (!window.observer) {
		let callback = () => {
			nextTick(() => {
				updateList.forEach((fn) => {
					fn();
				});
			});
		};
		window.observer = useMutationObserver(container as HTMLElement, callback, {
			attributes: true,
			childList: true,
			subtree: true,
			attributeFilter: ["style", "class"],
			characterData: true,
		});
	}
	watchEffect(() => {
		host.style.width = addPxToNumber(targetBounds.width, false);
		host.style.height = addPxToNumber(targetBounds.height, false);
		host.style.top = addPxToNumber(targetBounds.top, false);
		host.style.left = addPxToNumber(targetBounds.left, false);
	});

	return targetBounds.update;
}

export default trackTarget;
