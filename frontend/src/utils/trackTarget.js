import { useElementBounding, useEventListener, useMutationObserver } from "@vueuse/core";
import { nextTick, reactive, watch } from "vue";
import useStore from "../store";
const store = useStore();

window.observer = null;
const updateList = [];
// TODO: Remove padding from here or rename
function trackTarget(target, host, padding = 0) {
	let targetBounds = reactive(useElementBounding(target));
	let container = target.closest(".canvas-container");
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
