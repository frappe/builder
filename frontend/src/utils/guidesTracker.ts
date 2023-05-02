import { useElementBounding } from "@vueuse/core";
import { reactive } from "vue";
import useStore from "../store";
const store = useStore();
const tracks = [{
	point: 0,
	strength: 10
}, {
	point: 0.25,
	strength: 2
}, {
	point: 0.5,
	strength: 10
}, {
	point: 0.75,
	strength: 2
}, {
	point: 1,
	strength: 10
}];

function setGuides(target: HTMLElement) {
	const threshold = 10;
	// TODO: Remove canvas dependency
	const canvasElement = target.closest(".canvas") as HTMLElement;
	const canvasBounds = reactive(useElementBounding(canvasElement));
	const targetBounds = reactive(useElementBounding(target));
	const parentBounds = reactive(useElementBounding(target.parentElement as HTMLElement));

	const getFinalWidth = (calculatedWidth: number) => {
		targetBounds.update();
		canvasBounds.update();
		parentBounds.update();

		const scale = store.canvas.scale;
		const targetRight = targetBounds.left + calculatedWidth * scale;

		let finalWidth = calculatedWidth;
		let set = false;
		tracks.forEach((track) => {
			const canvasRight = canvasBounds.left + (canvasBounds.width * track.point);
			const parentRight = parentBounds.left + (parentBounds.width * track.point);
			if (Math.abs(targetRight - canvasRight) < track.strength) {
				finalWidth = (canvasRight - targetBounds.left) / scale;
				store.guides.x = canvasRight;
				set = true;
			} else if (Math.abs(targetRight - parentRight) < track.strength) {
				finalWidth = (parentRight - targetBounds.left) / scale;
				store.guides.x = parentRight;
				set = true;
			}
		})

		if (!set) {
			store.guides.x = -1;
		}

		return Math.round(finalWidth);
	};

	const getFinalHeight = (calculatedHeight: number) => {
		targetBounds.update();
		canvasBounds.update();
		parentBounds.update();

		const scale = store.canvas.scale;
		const targetBottom = targetBounds.top + calculatedHeight * scale;

		let finalHeight = calculatedHeight;
		let set = false;
		tracks.forEach((track) => {
			const canvasBottom = canvasBounds.top + (canvasBounds.height * track.point);
			const parentBottom = parentBounds.top + (parentBounds.height * track.point);
			if (Math.abs(targetBottom - canvasBottom) < track.strength) {
				finalHeight = (canvasBottom - targetBounds.top) / scale;
				store.guides.y = canvasBottom;
				set = true;
			} else if (Math.abs(targetBottom - parentBottom) < track.strength) {
				finalHeight = (parentBottom - targetBounds.top) / scale;
				store.guides.y = parentBottom;
				set = true;
			}
		})

		if (!set) {
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
