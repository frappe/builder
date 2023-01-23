function setPanAndZoom(element, zoomLimits = { min: 0.5, max: 2 }) {
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
			{ passive: false },
		);

		element.addEventListener("dblclick", () => {
			element.style.transform = "";
			element.previousX = 0;
			element.previousY = 0;
			element.previousScale = 1;
		});
	}
}

export default setPanAndZoom;
