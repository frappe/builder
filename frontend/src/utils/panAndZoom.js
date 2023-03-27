import useStore from "./../store";
const store = useStore();
import { useElementBounding } from "@vueuse/core";
import { nextTick, reactive } from "vue";


function setPanAndZoom(
	props,
	target,
	panAndZoomAreaElement,
	zoomLimits = { min: 0.2, max: 10 }
) {
	const targetBound = reactive(useElementBounding(target));
	let scale = props.scale || 1;
	let pointFromCenterX = 0;
	let pointFromCenterY = 0;
	let startX = 0;
	let startY = 0;
	let pinchPointSet = false;

	panAndZoomAreaElement.addEventListener(
		"wheel",
		(e) => {
			e.preventDefault();
			if (e.ctrlKey) {
				// Multiplying with 0.01 to make the zooming less sensitive
				// Multiplying with scale to make the zooming feel consistent
				scale -= e.deltaY * 0.01 * props.scale;
				scale = Math.min(Math.max(scale, zoomLimits.min), zoomLimits.max);
				props.scale = scale;
				nextTick(() => {
					targetBound.update();
					if (!pinchPointSet) {
						pointFromCenterX = (e.clientX - (targetBound.left + (targetBound.width / 2))) / scale;
						pointFromCenterY = (e.clientY - (targetBound.top + (targetBound.height / 2))) / scale;
						startX = e.clientX;
						startY = e.clientY;
						pinchPointSet = true;
						let clearPinchPoint = () => {
							pinchPointSet = false;
							panAndZoomAreaElement.removeEventListener("mousemove", clearPinchPoint);
						};
						panAndZoomAreaElement.addEventListener("mousemove", clearPinchPoint);
					}

					let pinchLocationX = targetBound.left + (targetBound.width / 2) + (pointFromCenterX * scale);
					let pinchLocationY = targetBound.top + (targetBound.height / 2) + (pointFromCenterY * scale);

					let diffX = startX - pinchLocationX;
					let diffY = startY - pinchLocationY;

					props.translateX += (diffX / scale);
					props.translateY += (diffY / scale);
				})
			} else {
				pinchPointSet = false;
				// Dividing with scale to make the panning feel consistent
				props.translateX -= e.deltaX * 2 / props.scale;
				props.translateY -= e.deltaY * 2 / props.scale;
			}
		},
		{ passive: false }
	);

	target.addEventListener("dblclick", () => {
		props.scale = store.canvas.initialScale;
		props.translateX = 0;
		props.translateY = store.canvas.initialTranslateY;
	});
}

export default setPanAndZoom;
