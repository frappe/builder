import DOMPurify from "dompurify";

/** Static layout drawings only; no links, remote assets, CSS, animation or embedded HTML. */
export function sanitizeLayoutSVG(value: unknown): string {
	if (typeof value !== "string" || !value.trim()) return "";
	const fragment = DOMPurify.sanitize(value, {
		ALLOWED_TAGS: [
			"svg",
			"g",
			"rect",
			"circle",
			"ellipse",
			"line",
			"polyline",
			"polygon",
			"path",
			"text",
			"tspan",
		],
		ALLOWED_ATTR: [
			"viewBox",
			"width",
			"height",
			"x",
			"y",
			"x1",
			"x2",
			"y1",
			"y2",
			"cx",
			"cy",
			"r",
			"rx",
			"ry",
			"d",
			"points",
			"fill",
			"stroke",
			"stroke-width",
			"opacity",
			"transform",
			"font-size",
			"font-weight",
			"text-anchor",
		],
		RETURN_DOM: true,
	}) as Element;
	for (const node of fragment.querySelectorAll("[fill], [stroke]")) {
		for (const attribute of ["fill", "stroke"]) {
			const color = node.getAttribute(attribute);
			if (color && !/^(#[\da-f]{3,8}|[a-z]+|(?:rgb|hsl)a?\([\d\s.,%+-]+\))$/i.test(color)) {
				node.removeAttribute(attribute);
			}
		}
	}
	return fragment.querySelector("svg")?.outerHTML || "";
}
