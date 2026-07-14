// Builds a CSS cursor from an SVG rotated around its hotspot.
function getRotatedCursor(svg: string, angle: number, fallback: string, hotspot = 16): string {
	const rotatedSvg = svg.replace(
		'<g fill="none" fill-rule="evenodd">',
		`<g fill="none" fill-rule="evenodd" transform="rotate(${angle} ${hotspot} ${hotspot})">`,
	);
	// Makes the SVG safe for a quoted data URI.
	const dataUri = rotatedSvg
		.replace(/>\s+</g, "><")
		.trim()
		.replace(/"/g, "'")
		.replace(/%/g, "%25")
		.replace(/#/g, "%23");
	return `url("data:image/svg+xml,${dataUri}") ${hotspot} ${hotspot}, ${fallback}`;
}

let overlay: HTMLDivElement | null = null;

// Prevents hovered elements from overriding the cursor during a drag.
function setDragCursor(cursor: string) {
	if (!overlay) {
		overlay = document.createElement("div");
		overlay.style.position = "fixed";
		overlay.style.inset = "0";
		overlay.style.zIndex = "2147483647";
		document.body.appendChild(overlay);
	}
	overlay.style.cursor = cursor;
}

function clearDragCursor() {
	overlay?.remove();
	overlay = null;
}

type DragOptions = {
	cursor?: string;
	onMove: (event: MouseEvent) => void;
	onEnd?: (event: MouseEvent) => void;
};

// Runs a mouse drag with the cursor locked for its duration, tearing down its listeners on mouseup.
function startDrag({ cursor, onMove, onEnd }: DragOptions) {
	if (cursor) setDragCursor(cursor);

	const mousemove = (moveEvent: MouseEvent) => {
		onMove(moveEvent);
		moveEvent.preventDefault();
	};

	document.addEventListener("mousemove", mousemove);
	document.addEventListener(
		"mouseup",
		(upEvent) => {
			document.removeEventListener("mousemove", mousemove);
			clearDragCursor();
			onEnd?.(upEvent);
			upEvent.preventDefault();
		},
		{ once: true },
	);
}

export { clearDragCursor, getRotatedCursor, setDragCursor, startDrag };
