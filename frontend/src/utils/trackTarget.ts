import { useElementBounding, useMutationObserver } from "@vueuse/core";
import { nextTick, reactive, watch } from "vue";
import useStore from "../store";
import { addPxToNumber } from "./helpers";
const store = useStore();

declare global {
	interface Window {
		observer: any;
	}
}

window.observer = null;
const updateList: (() => void)[] = [];

function trackTarget(target: HTMLElement, host: HTMLElement) {
	const targetBounds = reactive(useElementBounding(target));
	const container = target.closest(".canvas-container");
	// TODO: too much? find a better way to track changes
	updateList.push(targetBounds.update);
	watch(store.canvas, () => nextTick(targetBounds.update), { deep: true });
	watch(store.componentEditor, () => nextTick(targetBounds.update), { deep: true });

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
	watch(targetBounds, () => {
		host.style.width = addPxToNumber(targetBounds.width - 1, false);
		host.style.height = addPxToNumber(targetBounds.height - 1, false);
		host.style.top = addPxToNumber(targetBounds.top, false);
		host.style.left = addPxToNumber(targetBounds.left, false);
	});

	return targetBounds.update;
}

export default trackTarget;
