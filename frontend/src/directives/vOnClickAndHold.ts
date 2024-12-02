import { DirectiveBinding } from "vue";

const vOnClickAndHold = {
	mounted(el: HTMLElement, binding: DirectiveBinding) {
		let timer: ReturnType<typeof setTimeout>;
		el.addEventListener("mousedown", () => {
			timer = setTimeout(() => {
				binding.value();
			}, 300);
			document.addEventListener(
				"mouseup",
				() => {
					clearTimeout(timer);
				},
				{ once: true },
			);
		});
	},
};

export default vOnClickAndHold;
