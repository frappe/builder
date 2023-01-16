export { set_pan_and_zoom };

function set_pan_and_zoom(element, zoom_limits = { min: 0.5, max: 2 }) {
	if (element.parentElement) {
		element.parentElement.addEventListener(
			"wheel",
			function (e) {
				e.preventDefault();
				let scale = element.previousScale || 1;
				let x = element.previousX || 0;
				let y = element.previousY || 0;

				if (e.ctrlKey) {
					scale -= e.deltaY * 0.01;
					if (scale < zoom_limits.min) scale = zoom_limits.min;
					if (scale > zoom_limits.max) scale = zoom_limits.max;
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

		function set_reset_event(element) {
			element.addEventListener("dblclick", function (e) {
				element.style.transform = "";
				element.previousX = 0;
				element.previousY = 0;
				element.previousScale = 1;
			});
		}
		set_reset_event(element);
	}
}
