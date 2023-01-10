export { set_pan_and_zoom }

function set_pan_and_zoom(element, zoom_limits = { min: 0.5, max: 2 }) {
	if (element.parentElement) {
		element.parentElement.addEventListener('mousemove', function (e) {
			if (e.buttons === 1) {
				let x = (element.previousX || 0) + e.movementX
				let y = (element.previousY || 0) + e.movementY
				element.style.transform = `translate(${x}px, ${y}px) scale(${
					element.previousScale || 1
				})`
				element.previousX = x
				element.previousY = y
			}
		})

		element.parentElement.addEventListener('wheel', function (e) {
			e.preventDefault()
			let scale = (element.previousScale || 1) + e.deltaY * -0.01
			if (scale < zoom_limits.min) scale = zoom_limits.min
			if (scale > zoom_limits.max) scale = zoom_limits.max
			element.style.transform = `scale(${scale}) translate(${
				element.previousX || 0
			}px, ${element.previousY || 0}px)`
			element.previousScale = scale
		})

		function set_reset_event(element) {
			element.addEventListener('dblclick', function (e) {
				element.style.transform = ''
				element.previousX = 0
				element.previousY = 0
				element.previousScale = 1
			})
		}
		set_reset_event(element)
	}
}
