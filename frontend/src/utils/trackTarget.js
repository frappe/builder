import { useElementBounding, useEventListener, useMutationObserver } from "@vueuse/core";
import { nextTick, reactive, watch } from "vue";

window.observer = null;
const updateList = [];

// TODO: Remove padding from here or rename
function trackTarget(target, host, padding = 0) {
	let targetBounds = reactive(useElementBounding(target));
	let container = target.closest(".canvas-container");
	useEventListener(container, "wheel", targetBounds.update);
	// TODO: too much? find a better way to track changes
	updateList.push(targetBounds.update);
	if (!window.observer) {
		let callback = () => {
			nextTick(() => {
				updateList.forEach((fn) => {
					fn();
				})
			});
		}
		window.observer =  useMutationObserver(container, callback, {
			attributes: true,
			childList: true,
			subtree: true,
			attributeFilter: ["style", "class"],
			characterData: true
		});
	}
	watch(targetBounds, () => {
			host.style.width = `${targetBounds.width - padding}px`;
			host.style.height = `${targetBounds.height - padding}px`;
			host.style.top = `${targetBounds.top + padding/2}px`;
			host.style.left = `${targetBounds.left + padding/2}px`;
	});
}

export default trackTarget;