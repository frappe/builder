function setPanAndZoom(
	props,
	target,
	panAndZoomAreaElement,
	zoomLimits = { min: 0.2, max: 10 }
) {
	let scale = props.scale || 1;
	let x = props.translateX || 0;
	let y = props.translateY || 0;
	let pointFromCenterX = 0;
	let pointFromCenterY = 0;
	let initialTranslateX = 0;
	let initialTranslateY = 0;
	let initialScale = 1;

	panAndZoomAreaElement.addEventListener(
		"wheel",
		(e) => {
			e.preventDefault();
			if (e.ctrlKey) {
				// Multiplying with 0.01 to make the zooming less sensitive
				// Multiplying with scale to make the zooming feel consistent
				scale -= e.deltaY * 0.01 * props.scale;

				if (scale < zoomLimits.min) scale = zoomLimits.min;
				if (scale > zoomLimits.max) scale = zoomLimits.max;
				let targetBound = target.getBoundingClientRect();

				if (!pointFromCenterX) {
					initialScale = props.scale;
					pointFromCenterX = (e.clientX - (targetBound.left + (targetBound.width / 2))) / initialScale;
					pointFromCenterY = (e.clientY - (targetBound.top + (targetBound.height / 2))) / initialScale;
					props.startX = e.clientX;
					props.startY = e.clientY;
					initialTranslateX = props.translateX;
					initialTranslateY = props.translateY;
					let clearPointFromCenter = () => {
						pointFromCenterX = null;
						panAndZoomAreaElement.removeEventListener("mousemove", clearPointFromCenter);
					};
					panAndZoomAreaElement.addEventListener("mousemove", clearPointFromCenter);
				}

				props.translateX = (pointFromCenterX / scale) - pointFromCenterX;
				props.translateY = (pointFromCenterY / scale) - pointFromCenterY;

				props.pinchPointX = `${pointFromCenterX}px`;
				props.pinchPointY = `${pointFromCenterY}px`;

				props.scale = scale;

			} else {
				pointFromCenterX = null;
				// Dividing with scale to make the panning feel consistent
				x -= e.deltaX * 2 / props.scale;
				y -= e.deltaY * 2 / props.scale;
				props.translateX = x;
				props.translateY = y;
			}
		},
		{ passive: false }
	);

	target.addEventListener("dblclick", () => {
		props.scale = 1;
		props.translateX = 0;
		props.translateY = 0;
	});
}

export default setPanAndZoom;
