function setPanAndZoom(
	props,
	target,
	panAndZoomAreaElement,
	zoomLimits = { min: 0.5, max: 2 }
) {
	let scale = props.scale || 1;
	let x = props.translateX || 0;
	let y = props.translateY || 0;

	panAndZoomAreaElement.addEventListener(
		"wheel",
		(e) => {
			e.preventDefault();
			if (e.ctrlKey) {
				scale -= e.deltaY * 0.01;
				if (scale < zoomLimits.min) scale = zoomLimits.min;
				if (scale > zoomLimits.max) scale = zoomLimits.max;
				props.scale = scale;
			} else {
				x -= e.deltaX * 2;
				y -= e.deltaY * 2;
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
