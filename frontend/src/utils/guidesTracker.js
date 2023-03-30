import useStore from "../store";
import { reactive } from "vue";
import { useElementBounding } from "@vueuse/core";
const store = useStore();

function setGuides(target) {
	const threshold = 10;
	const canvasBounds = reactive(useElementBounding(document.querySelector(".canvas")));
	const targetBounds = reactive(useElementBounding(target));

	const getFinalWidth = (calculatedWidth) => {
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
		return finalWidth;
	};

	const getFinalHeight = (calculatedHeight) => {
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
		return finalHeight;
	};

	const getFinalLeft = (calculatedLeft) => {
		targetBounds.update();
		canvasBounds.update();
		let scale = store.canvas.scale;
		let finalLeft = calculatedLeft;

		const targetRight = targetBounds.left + calculatedLeft * scale;
		const canvasHalf = canvasBounds.left + canvasBounds.width / 2;

		if (Math.abs(targetRight - canvasBounds.right) < threshold) {
			finalLeft = (canvasBounds.right - targetBounds.left) / scale;
			store.guides.x = canvasBounds.right;
		} else if (Math.abs(targetRight - canvasHalf) < threshold) {
			finalLeft = (canvasHalf - targetBounds.left) / scale;
			store.guides.x = canvasHalf;
		} else {
			store.guides.x = -1;
		}
		return finalLeft;

	};





	const showX = (x) => {
		store.guides.x = -1;
		store.guides.showX = true;
	};
	const showY = (y) => {
		store.guides.y = -1;
		store.guides.showY = true;
	};
	const hideX = () => {
		store.guides.showX = false;
	};
	const hideY = () => {
		store.guides.showY = false;
	};

	return { getFinalWidth, getFinalHeight, showX, showY, hideX, hideY, getFinalLeft };
}

export default setGuides;
