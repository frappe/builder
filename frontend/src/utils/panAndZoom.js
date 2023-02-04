function setPanAndZoom(element, zoomLimits = { min: 0.5, max: 2 }) {
	const initialScale = element.previousScale || 1;
	const initialX = element.previousX || 0;
	const initialY = element.previousY || 0;
	if (element.parentElement) {
		element.parentElement.addEventListener(
			"wheel",
			(e) => {
				e.preventDefault();
				let scale = element.previousScale || 1;
				let x = element.previousX || 0;
				let y = element.previousY || 0;

				if (e.ctrlKey) {
					scale -= e.deltaY * 0.01;
					if (scale < zoomLimits.min) scale = zoomLimits.min;
					if (scale > zoomLimits.max) scale = zoomLimits.max;
					element.style.transform = `scale(${scale}) translate(${
						element.previousX || 0
					}px, ${element.previousY || 0}px)`;
					element.previousScale = scale;
				} else {
					x -= e.deltaX * 2;
					y -= e.deltaY * 2;
					element.style.transform = `translate(${x}px, ${y}px) scale(${
						element.previousScale || 1
					})`;
					element.previousX = x;
					element.previousY = y;
				}
			},
			{ passive: false }
		);

		element.addEventListener("dblclick", () => {
			element.style.transform = `translate(${initialX}px, ${initialY}px) scale(${initialScale})`;
			element.previousX = initialX;
			element.previousY = initialY;
			element.previousScale = initialScale;
		});
	}
}

export default setPanAndZoom;
