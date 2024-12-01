import { DirectiveBinding } from "vue";

const vOnClickAndHold = {
	mounted(el: HTMLElement, binding: DirectiveBinding) {
		let timer: ReturnType<typeof setTimeout>;
		function captureClick(e: MouseEvent) {
			e.preventDefault();
		}
		el.addEventListener("mousedown", () => {
			timer = setTimeout(() => {
				binding.value();
				// skip click event once hold event is triggered
				window.addEventListener("click", captureClick, true);
			}, 500);
			document.addEventListener(
				"mouseup",
				() => {
					clearTimeout(timer);
					requestAnimationFrame(() => {
						window.removeEventListener("click", captureClick, true);
					});
				},
				{ once: true },
			);
		});
	},
};

export default vOnClickAndHold;
