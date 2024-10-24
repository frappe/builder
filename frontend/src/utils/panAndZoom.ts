import { useElementBounding } from "@vueuse/core";
import { nextTick, reactive } from "vue";

function setPanAndZoom(
	target: HTMLElement,
	panAndZoomAreaElement: HTMLElement,
	props: CanvasProps,
	zoomLimits = { min: 0.1, max: 10 },
) {
	const targetBound = reactive(useElementBounding(target));
	let pointFromCenterX = 0;
	let pointFromCenterY = 0;
	let startX = 0;
	let startY = 0;
	let pinchPointSet = false;
	let wheeling: undefined | NodeJS.Timeout;

	const updatePanAndZoom = (e: WheelEvent) => {
		clearTimeout(wheeling);
		if (e.ctrlKey || e.metaKey) {
			props.scaling = true;
			if (!pinchPointSet) {
				// set pinch point before setting new scale value
				targetBound.update();
				const middleX = targetBound.left + targetBound.width / 2;
				const middleY = targetBound.top + targetBound.height / 2;
				pointFromCenterX = (e.clientX - middleX) / props.scale;
				pointFromCenterY = (e.clientY - middleY) / props.scale;
				startX = e.clientX;
				startY = e.clientY;
				pinchPointSet = true;
				let clearPinchPoint = () => {
					pinchPointSet = false;
				};
				panAndZoomAreaElement.addEventListener("mousemove", clearPinchPoint, { once: true });
			}

			let sensitivity = 0.008;
			function tooMuchScroll() {
				if (e.deltaY > 30 || e.deltaY < -30) {
					return true;
				}
			}
			if (tooMuchScroll()) {
				// If the user scrolls too much, reduce the sensitivity
				// this mostly happens when the user uses mouse wheel to scroll
				// probably not the best way to handle this, but works for now
				sensitivity = 0.001;
			}

			// Multiplying with scale to make the zooming feel consistent
			let scale = props.scale - e.deltaY * sensitivity * props.scale;
			scale = Math.min(Math.max(scale, zoomLimits.min), zoomLimits.max);
			props.scale = scale;
			nextTick(() => {
				targetBound.update();
				const middleX = targetBound.left + targetBound.width / 2;
				const middleY = targetBound.top + targetBound.height / 2;

				const pinchLocationX = middleX + pointFromCenterX * scale;
				const pinchLocationY = middleY + pointFromCenterY * scale;

				const diffX = startX - pinchLocationX;
				const diffY = startY - pinchLocationY;

				props.translateX += diffX / scale;
				props.translateY += diffY / scale;
			});
		} else {
			props.panning = true;
			pinchPointSet = false;
			// Dividing with scale to make the panning feel consistent
			props.translateX -= e.deltaX / props.scale;
			props.translateY -= e.deltaY / props.scale;
		}
		wheeling = setTimeout(() => {
			props.scaling = false;
			props.panning = false;
		}, 200);
	};

	panAndZoomAreaElement.addEventListener(
		"wheel",
		(e) => {
			e.preventDefault();
			requestAnimationFrame(() => updatePanAndZoom(e));
		},
		{ passive: false },
	);
}

export default setPanAndZoom;
