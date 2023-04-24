import { useElementBounding } from "@vueuse/core";
import { reactive } from "vue";
import useStore from "../store";
const store = useStore();

function setGuides(target: HTMLElement) {
	const threshold = 10;
	// TODO: Remove canvas dependency
	const canvasElement = document.getElementById("canvas") as HTMLElement;
	const canvasBounds = reactive(useElementBounding(canvasElement));
	const targetBounds = reactive(useElementBounding(target));

	const getFinalWidth = (calculatedWidth: number) => {
		targetBounds.update();
		canvasBounds.update();
		let scale = store.canvas.scale;
		let finalWidth = calculatedWidth;

		const targetRight = targetBounds.left + calculatedWidth * scale;
		const canvasHalf = canvasBounds.left + canvasBounds.width / 2;

		if (Math.abs(targetRight - canvasBounds.right) < threshold) {
			finalWidth = (canvasBounds.right - targetBounds.left) / scale;
			store.guides.x = canvasBounds.right;
		} else if (Math.abs(targetRight - canvasHalf) < threshold) {
			finalWidth = (canvasHalf - targetBounds.left) / scale;
			store.guides.x = canvasHalf;
		} else {
			store.guides.x = -1;
		}
		return Math.round(finalWidth);
	};

	const getFinalHeight = (calculatedHeight: number) => {
		targetBounds.update();
		canvasBounds.update();
		let scale = store.canvas.scale;
		let finalHeight = calculatedHeight;

		const targetBottom = targetBounds.top + calculatedHeight * scale;
		const canvasHalf = canvasBounds.top + canvasBounds.height / 2;

		if (Math.abs(targetBottom - canvasBounds.bottom) < threshold) {
			finalHeight = (canvasBounds.bottom - targetBounds.top) / scale;
			store.guides.y = canvasBounds.bottom;
		} else if (Math.abs(targetBottom - canvasHalf) < threshold) {
			finalHeight = (canvasHalf - targetBounds.top) / scale;
			store.guides.y = canvasHalf;
		} else {
			store.guides.y = -1;
		}
		return Math.round(finalHeight);
	};

	const getLeftPositionOffset = () => {
		targetBounds.update();
		canvasBounds.update();
		let scale = store.canvas.scale;
		let leftOffset = 0;

		const canvasHalf = canvasBounds.left + canvasBounds.width / 2;

		if (Math.abs(targetBounds.left - canvasBounds.left) < threshold) {
			leftOffset = (canvasBounds.left - targetBounds.left) / scale;
			store.guides.x = canvasBounds.left;
		} else if (Math.abs(targetBounds.left - canvasHalf) < threshold) {
			leftOffset = (canvasHalf - targetBounds.left) / scale;
			store.guides.x = canvasHalf;
		} else if (Math.abs(targetBounds.left - canvasBounds.right) < threshold) {
			leftOffset = (canvasBounds.right - targetBounds.left) / scale;
			store.guides.x = canvasBounds.right;
		} else {
			store.guides.x = -1;
		}
		return Math.round(leftOffset);
	};

	const showX = () => {
		store.guides.x = -1;
		store.guides.showX = true;
	};
	const showY = () => {
		store.guides.y = -1;
		store.guides.showY = true;
	};
	const hideX = () => {
		store.guides.showX = false;
	};
	const hideY = () => {
		store.guides.showY = false;
	};

	return {
		getFinalWidth,
		getFinalHeight,
		showX,
		showY,
		hideX,
		hideY,
		getLeftPositionOffset,
	};
}

export default setGuides;
