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
	onEnd?: (event?: MouseEvent) => void;
	// Escape aborts the drag; restore whatever was captured at mousedown. onEnd still runs after.
	onCancel?: () => void;
};

// Runs a mouse drag with the cursor locked for its duration, tearing down its listeners on mouseup.
function startDrag({ cursor, onMove, onEnd, onCancel }: DragOptions) {
	if (cursor) setDragCursor(cursor);

	const mousemove = (moveEvent: MouseEvent) => {
		onMove(moveEvent);
		moveEvent.preventDefault();
	};

	const stop = () => {
		document.removeEventListener("mousemove", mousemove);
		document.removeEventListener("mouseup", mouseup);
		document.removeEventListener("keydown", keydown);
		clearDragCursor();
	};

	const mouseup = (upEvent: MouseEvent) => {
		stop();
		onEnd?.(upEvent);
		upEvent.preventDefault();
	};

	// Dropping the mouseup listener keeps the pending release from ending the drag a second time.
	const keydown = (keyEvent: KeyboardEvent) => {
		if (keyEvent.key !== "Escape") return;
		keyEvent.preventDefault();
		stop();
		onCancel?.();
		onEnd?.();
	};

	document.addEventListener("mousemove", mousemove);
	document.addEventListener("mouseup", mouseup);
	document.addEventListener("keydown", keydown);
}

export { clearDragCursor, getRotatedCursor, setDragCursor, startDrag };
