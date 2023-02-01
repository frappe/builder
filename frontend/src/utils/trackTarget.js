import { useElementBounding, useEventListener, useMutationObserver } from "@vueuse/core";
import { reactive, watch } from "vue";

function trackTarget(target, host) {
	let targetBounds = reactive(useElementBounding(target));
	let container = target.closest(".canvas-container");
	useEventListener(container, "wheel", targetBounds.update);
	useMutationObserver(target, targetBounds.update, { attributes: true });
	watch(targetBounds, () => {
		host.style.width = `${targetBounds.width}px`;
		host.style.height = `${targetBounds.height}px`;
		host.style.top = `${targetBounds.top}px`;
		host.style.left = `${targetBounds.left}px`;
	});
}

export default trackTarget;