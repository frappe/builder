export default function spacer(target, parent=null) {
	let { left, right, top, bottom } = (parent || document.body).getBoundingClientRect();
	let helper_template = document.createElement("template");
	helper_template.innerHTML = `
		<div class="helper z-10 fixed pointer-events-none">
			<div class="left left-0 bg-purple-700 w-1 opacity-20 h-full absolute hover:opacity-30 pointer-events-auto cursor-ew-resize"></div>
			<div class="right right-0 bg-purple-700 w-1 opacity-20 h-full absolute hover:opacity-30 pointer-events-auto cursor-ew-resize"></div>
		</div>
	`.trim();
	let helper = helper_template.content.firstChild;
	document.getElementsByClassName("overlay")[0].append(helper);

	let right_handle = helper.querySelector(".right");
	let left_handle = helper.querySelector(".left");

	function update_helper() {
		let client_bounds = target.getBoundingClientRect();
		helper.style.top =  client_bounds.top + "px";
		helper.style.left =  client_bounds.left + "px";
		helper.style.width = client_bounds.width + "px";
		helper.style.height = client_bounds.height + "px";
	}


	left_handle.addEventListener("mousedown", (e) => {
		let start_x = e.clientX;
		// to disable cursor jitter
		let doc_cursor = document.body.style.cursor;
		document.body.style.cursor =
			window.getComputedStyle(left_handle)["cursor"];

		let mousemove = (e) => {
			let movement = e.clientX - start_x;
			// no negative margins
			if (movement < 0) movement = 0;
			target.style.margin = `0 ${movement}px`;
			e.preventDefault();
		};
		document.addEventListener("mousemove", mousemove);
		document.addEventListener("mouseup", (e) => {
			document.body.style.cursor = doc_cursor;
			document.removeEventListener("mousemove", mousemove);
			e.preventDefault();
		});
	})

	let margin_classes = ["mx-0", "mx-1", "mx-2", "mx-3", "mx-4", "mx-5", "mx-6", "mx-7", "mx-8", "mx-9", "mx-10", "mx-11", "mx-12", "mx-14", "mx-16", "mx-20", "mx-24", "mx-28", "mx-32", "mx-36", "mx-40", "mx-44", "mx-48", "mx-52", "mx-56", "mx-60", "mx-64", "mx-72", "mx-80", "mx-96"];

	update_helper();

	target.closest(".canvas-container").addEventListener("wheel", update_helper);
	window.addEventListener("resize", update_helper);
	window.addEventListener("scroll", update_helper);

	let observer = new MutationObserver(update_helper);
	const config = {
		attributes: true,
		subtree: true,
	};
	observer.observe(target, config);
	observer.observe(document.getElementsByClassName("canvas")[0], {
		...config,
		childList: true,
	});
}