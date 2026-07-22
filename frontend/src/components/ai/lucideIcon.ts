// Expands a Lucide icon name into an inline SVG string. The AI emits a compact
// `icon: <name>` reference (cheap tokens); we bake the full SVG here so it
// renders everywhere — editor canvas AND server-side published pages — with no
// icon dependency on the backend. The SVG uses stroke="currentColor", so it
// inherits the block's `color`.
//
// Source: `lucide-static` — the same Lucide package frappe-ui already depends on
// (raw SVG strings keyed by PascalCase), so we don't ship a second icon library.
import * as lucideStatic from "lucide-static";

const iconSet = lucideStatic as unknown as Record<string, string>;

/** "arrow-right" -> "ArrowRight", "building-2" -> "Building2" */
function toPascalCase(name: string): string {
	return name
		.trim()
		.split(/[-_\s]+/)
		.filter(Boolean)
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join("");
}

export function isLucideIcon(name: string): boolean {
	return Boolean(name && typeof iconSet[toPascalCase(name)] === "string");
}

/** Build an inline Lucide SVG string. The svg is sized to FILL its wrapper
 * (width/height 100%, viewBox preserved so it scales), so the icon's size is
 * driven by the wrapper block's width/height — editable later, not baked in.
 * stroke="currentColor" is kept, so the icon takes the wrapper's `color`.
 * Returns "" for unknown names (never throws). */
export function lucideSVG(name: string, strokeWidth = 2): string {
	const raw = iconSet[toPascalCase(name)];
	if (typeof raw !== "string") return "";
	return raw
		.replace(/\s*\n\s*/g, " ") // collapse the multi-line source to one line
		.replace(/\s*class="[^"]*"/, "") // drop `lucide lucide-*` (collides with frappe-ui's mask utility)
		.replace(/width="\d+"/, 'width="100%"')
		.replace(/height="\d+"/, 'height="100%"')
		.replace(/stroke-width="[\d.]+"/, `stroke-width="${strokeWidth}"`)
		.trim();
}
