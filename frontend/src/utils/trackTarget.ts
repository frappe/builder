import { useElementBounding, useEventListener, useMutationObserver } from "@vueuse/core";
import { nextTick, reactive, watch } from "vue";
import useStore from "../store";
const store = useStore();

declare global {
	interface Window {
		observer: any;
	}
}

window.observer = null;
const updateList: (() => void)[] = [];

// TODO: Remove padding from here or rename
function trackTarget(target: HTMLElement, host: HTMLElement, padding = 0) {
	const targetBounds = reactive(useElementBounding(target));
	const container = target.closest(".canvas-container");
	// TODO: too much? find a better way to track changes
	updateList.push(targetBounds.update);
	watch(store.canvas, () => nextTick(targetBounds.update), { deep: true })

	if (!window.observer) {
		let callback = () => {
			nextTick(() => {
				updateList.forEach((fn) => {
					fn();
				});
			});
		};
		window.observer = useMutationObserver(container, callback, {
			attributes: true,
			childList: true,
			subtree: true,
			attributeFilter: ["style", "class"],
			characterData: true,
		});
	}
	watch(targetBounds, () => {
		host.style.width = `${Math.floor(targetBounds.width - padding)}px`;
		host.style.height = `${Math.floor(targetBounds.height - padding)}px`;
		host.style.top = `${Math.floor(targetBounds.top + padding / 2)}px`;
		host.style.left = `${Math.floor(targetBounds.left + padding / 2)}px`;
	});

	return targetBounds.update;
}

export default trackTarget;
