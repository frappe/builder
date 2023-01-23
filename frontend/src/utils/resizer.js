import useStore from "../store";

const store = useStore();

export default function setResizer(target) {
	const templateHtml = `<div class="z-10 editor fixed hover:border-[1px] hover:border-blue-200">
			<div class="absolute w-[4px] border-none bg-transparent top-0 bottom-0 left-[-2px] left-handle cursor-ew-resize hidden pointer-events-auto"></div>
			<div class="absolute w-[4px] border-none bg-transparent top-0 bottom-0 right-[-2px] right-handle cursor-ew-resize hidden pointer-events-auto"></div>
			<div class="absolute h-[4px] border-none bg-transparent top-[-2px] right-0 left-0 top-handle cursor-ns-resize hidden pointer-events-auto"></div>
			<div class="absolute h-[4px] border-none bg-transparent bottom-[-2px] right-0 left-0 bottom-handle cursor-ns-resize hidden pointer-events-auto"></div>

			<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white top-[-4px] left-[-4px] cursor-nwse-resize hidden pointer-events-auto"></div>
			<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white bottom-[-4px] left-[-4px] cursor-nesw-resize hidden pointer-events-auto"></div>
			<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white top-[-4px] right-[-4px] cursor-nesw-resize hidden pointer-events-auto"></div>
			<div class="absolute w-[8px] h-[8px] border-[1px] border-blue-400 rounded-full bg-white bottom-[-4px] right-[-4px] cursor-nwse-resize hidden pointer-events-auto"></div>
		<div>`;

	const editorTemplate = document.createElement("template");
	editorTemplate.innerHTML = templateHtml;

	const editor = editorTemplate.content.firstChild;

	const rightHandle = editor.querySelector(".right-handle");
	rightHandle.addEventListener("mousedown", (ev) => {
		const startX = ev.clientX;
		const startWidth = target.offsetWidth;

		// to disable cursor jitter
		const docCursor = document.body.style.cursor;
		document.body.style.cursor = window.getComputedStyle(rightHandle).cursor;

		const mousemove = (mouseMoveEvent) => {
			const movement = mouseMoveEvent.clientX - startX;
			target.style.width = `${startWidth + movement}px`;
			mouseMoveEvent.preventDefault();
		};
		document.addEventListener("mousemove", mousemove);
		document.addEventListener("mouseup", (mouseUpEvent) => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
			mouseUpEvent.preventDefault();
		});
	});

	const bottomHandle = editor.querySelector(".bottom-handle");
	bottomHandle.addEventListener("mousedown", (e) => {
		const startY = e.clientY;
		const startHeight = target.offsetHeight;

		// to disable cursor jitter
		const docCursor = document.body.style.cursor;
		document.body.style.cursor =			window.getComputedStyle(bottomHandle).cursor;

		const mousemove = (mouseMoveEvent) => {
			const movement = mouseMoveEvent.clientY - startY;
			target.style.height = `${startHeight + movement}px`;
		};
		document.addEventListener("mousemove", mousemove);
		document.addEventListener("mouseup", () => {
			document.body.style.cursor = docCursor;
			document.removeEventListener("mousemove", mousemove);
		});
	});

	document.getElementsByClassName("overlay")[0].append(editor);

	function updateEditor() {
		const bound = target.getBoundingClientRect();
		editor.style.width = `${bound.width}px`;
		editor.style.height = `${bound.height}px`;
		editor.style.top = `${bound.top}px`;
		editor.style.right = `${bound.right}px`;
		editor.style.left = `${bound.left}px`;
		editor.style.right = `${bound.right}px`;
	}
	updateEditor();

	// TODO: sup buddy?
	target.closest(".canvas-container").addEventListener("wheel", updateEditor);

	window.addEventListener("resize", updateEditor);
	window.addEventListener("scroll", updateEditor);

	const observer = new MutationObserver(updateEditor);
	const config = {
		attributes: true,
		subtree: true,
	};
	observer.observe(target, config);
	observer.observe(document.getElementsByClassName("canvas")[0], {
		...config,
		childList: true,
	});

	editor.addEventListener("click", (e) => {
		e.stopPropagation();
		target.click();
	});

	if (store.selectedComponent === target) {
		// selected
		editor.querySelectorAll("[class*=resize]").forEach((element) => {
			element.classList.remove("hidden");
		});
		editor.classList.add(
			"pointer-events-none",
			"border-[1px]",
			"border-blue-400",
		);
	}

	store.$subscribe(({ events }) => {
		if (events.key !== "selectedComponent") return;
		if (events.newValue === target) {
			// selected
			editor.querySelectorAll("[class*=resize]").forEach((element) => {
				element.classList.remove("hidden");
			});
			editor.classList.add(
				"pointer-events-none",
				"border-[1px]",
				"border-blue-400",
			);
		} else {
			// un-selected
			editor.querySelectorAll("[class*=resize]").forEach((element) => {
				element.classList.add("hidden");
			});
			editor.classList.remove(
				"border-[1px]",
				"border-blue-400",
				// if the new selected component is a child of this component
				target.contains(events.newValue) ? "pointer-events-none" : null,
			);
		}
	});
}
