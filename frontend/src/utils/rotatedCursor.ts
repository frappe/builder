// Builds a `cursor` value from an SVG cursor icon rotated by `angle` degrees around
// its center, so custom cursors can stay visually aligned with a rotated block.
// `fallback` is a native cursor keyword shown while the data URI decodes/if unsupported.
function getRotatedCursor(svg: string, angle: number, fallback: string, hotspot = 16): string {
	const rotatedSvg = svg.replace(
		'<g fill="none" fill-rule="evenodd">',
		`<g fill="none" fill-rule="evenodd" transform="rotate(${angle} ${hotspot} ${hotspot})">`,
	);
	// minimal data-URI escaping: collapse the pretty-printed whitespace (raw newlines
	// aren't valid inside a CSS quoted string), swap to single quotes so the SVG's
	// attributes don't clash with the outer url("...") quoting, and escape only the
	// two characters that are actually unsafe in a bare data URI (# and %)
	const dataUri = rotatedSvg
		.replace(/>\s+</g, "><")
		.trim()
		.replace(/"/g, "'")
		.replace(/%/g, "%25")
		.replace(/#/g, "%23");
	return `url("data:image/svg+xml,${dataUri}") ${hotspot} ${hotspot}, ${fallback}`;
}

export default getRotatedCursor;
