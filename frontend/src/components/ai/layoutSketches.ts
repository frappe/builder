/** Deterministic wireframe sketches for the design-direction cards.
 *
 * The model names one of the generator's layout systems (~3 tokens) and the
 * option's palette; the sketch itself is drawn here, once, by hand — replacing
 * the per-option model-drawn SVGs (hundreds of tokens each, quality varying
 * per generation). Each sketch is flat rects in the option's own colours,
 * composed to make the structural difference between systems visible.
 */

const SAFE_COLOR = /^(#[0-9a-fA-F]{3,8}|rgba?\([\d\s.,%]+\)|hsla?\([\d\s.,%deg]+\)|[a-zA-Z]{3,20})$/;

function safe(color: unknown): string | null {
	const value = String(color ?? "").trim();
	return SAFE_COLOR.test(value) ? value : null;
}

/** Perceived-luminance check so text bars contrast with the option background. */
function isDark(hex: string): boolean {
	const m = hex.match(/^#([0-9a-fA-F]{6})/);
	if (!m) return false;
	const n = parseInt(m[1], 16);
	const [r, g, b] = [n >> 16, (n >> 8) & 255, n & 255];
	return 0.299 * r + 0.587 * g + 0.114 * b < 128;
}

function rect(x: number, y: number, w: number, h: number, fill: string, extra = ""): string {
	return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" ${extra}/>`;
}

type Palette = { bg: string; accent: string; ink: string; soft: string };

const SKETCHES: Record<string, (p: Palette) => string> = {
	"editorial-grid": ({ ink, accent, soft }) =>
		rect(8, 10, 104, 11, ink) +
		rect(8, 27, 104, 0.8, soft) +
		rect(8, 34, 26, 3, soft) +
		rect(8, 40, 22, 3, soft) +
		rect(8, 50, 64, 22, accent) +
		rect(80, 34, 32, 3, soft) +
		rect(80, 40, 28, 3, soft) +
		rect(80, 50, 32, 22, soft),
	"split-screen": ({ ink, accent, soft }) =>
		rect(0, 0, 54, 80, accent) +
		rect(62, 16, 48, 9, ink) +
		rect(62, 32, 40, 3, soft) +
		rect(62, 38, 36, 3, soft) +
		rect(62, 44, 42, 3, soft) +
		rect(62, 56, 22, 8, ink, 'rx="2"'),
	bento: ({ ink, accent, soft }) =>
		rect(8, 8, 62, 44, accent, 'rx="4"') +
		rect(74, 8, 38, 20, soft, 'rx="4"') +
		rect(74, 32, 38, 20, ink, 'rx="4"') +
		rect(8, 56, 104, 16, soft, 'rx="4"'),
	"poster-brutalist": ({ ink, accent }) =>
		`<rect x="4" y="4" width="112" height="72" fill="none" stroke="${ink}" stroke-width="2.5"/>` +
		rect(12, 14, 96, 15, ink) +
		rect(12, 33, 72, 15, accent, `transform="rotate(-3 48 40)"`) +
		rect(12, 60, 30, 4, ink) +
		rect(52, 60, 18, 4, ink),
	"dense-utility": ({ ink, soft }) =>
		[0, 1, 2, 3, 4]
			.map(
				(row) =>
					rect(8, 10 + row * 13, 34, 3.5, ink) +
					rect(92, 10 + row * 13, 20, 3.5, soft) +
					rect(8, 18 + row * 13, 104, 0.7, soft),
			)
			.join(""),
	"single-object": ({ ink, accent }) =>
		`<ellipse cx="60" cy="40" rx="44" ry="30" fill="${accent}" opacity="0.28"/>` +
		rect(42, 16, 36, 44, accent, 'rx="3"') +
		rect(48, 66, 24, 3, ink),
	"zine-collage": ({ ink, accent, soft }) =>
		rect(14, 12, 44, 32, accent, `transform="rotate(-4 36 28)"`) +
		rect(52, 26, 46, 34, soft, `transform="rotate(3 75 43)"`) +
		rect(32, 56, 34, 8, ink, `transform="rotate(-2 49 60)"`) +
		rect(12, 68, 20, 3, ink),
	"classic-centered": ({ ink, accent, soft }) =>
		rect(52, 11, 16, 3, soft) +
		rect(30, 19, 60, 9, ink) +
		rect(40, 33, 40, 3.5, soft) +
		rect(52, 43, 16, 7, accent, 'rx="2"') +
		rect(14, 58, 28, 14, soft, 'rx="2"') +
		rect(46, 58, 28, 14, soft, 'rx="2"') +
		rect(78, 58, 28, 14, soft, 'rx="2"'),
};

// Tolerated aliases for the prompt's looser namings.
const ALIASES: Record<string, string> = {
	"single-object-stage": "single-object",
	"single-stage": "single-object",
	poster: "poster-brutalist",
	editorial: "editorial-grid",
	split: "split-screen",
	zine: "zine-collage",
	centered: "classic-centered",
	classic: "classic-centered",
};

export function layoutSketch(layout: unknown, colors: unknown[] = []): string | null {
	const key = String(layout ?? "")
		.trim()
		.toLowerCase();
	const draw = SKETCHES[key] || SKETCHES[ALIASES[key]];
	if (!draw) return null;
	const bg = safe(colors[0]) || "#F4F1EA";
	const dark = isDark(bg);
	const ink = safe(colors[2]) || (dark ? "#F2EFE9" : "#17150F");
	const palette: Palette = {
		bg,
		accent: safe(colors[1]) || (dark ? "#8A8FA3" : "#B7B0A2"),
		ink,
		soft: `${ink}55`,
	};
	return (
		`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">` +
		rect(0, 0, 120, 80, palette.bg) +
		draw(palette) +
		`</svg>`
	);
}
