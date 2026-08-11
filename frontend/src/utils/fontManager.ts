import userFont from "@/data/userFonts";
import { useBuilderToken } from "@/utils/useBuilderToken";
import { shallowRef } from "vue";

interface FontListItem {
	family: string;
	variants: string[];
}

type FontWeight = "100" | "200" | "300" | "400" | "500" | "600" | "700" | "800" | "900";
interface WeightOption {
	value: FontWeight;
	label: string;
}

const WEIGHT_LABELS: Record<FontWeight, string> = {
	"100": "Thin",
	"200": "Extra Light",
	"300": "Light",
	"400": "Regular",
	"500": "Medium",
	"600": "Semi Bold",
	"700": "Bold",
	"800": "Extra Bold",
	"900": "Black",
};

const GF_CSS = "https://fonts.googleapis.com/css2";
const fontCache = new Map<string, Promise<string>>();

// A preview only ever renders the family's own name, so it loads a subset holding just
// those glyphs (~1KB instead of the full face). That face must NOT be registered under
// the real family name: a block that later applies the same font would otherwise race
// against a face carrying a handful of glyphs. Alias it instead.
const PREVIEW_PREFIX = "__builder_preview_";
// the picker re-queries on every keystroke, so batch the resulting loads
const PREVIEW_DEBOUNCE = 120;

const previewRequests = new Map<string, Promise<void>>();
// family -> the family its preview renders with; reactive so pickers restyle on arrival
const previewFamilies = shallowRef(new Map<string, string>());

// the Google Fonts catalog is ~110KB, so it stays out of the main bundle
// and loads on first use (font pickers read the reactive ref)
const fontListItems = shallowRef<FontListItem[]>([]);
let fontListPromise: Promise<FontListItem[]> | null = null;

export function loadFontList(): Promise<FontListItem[]> {
	if (!fontListPromise) {
		fontListPromise = import("@/utils/fontList.json").then((m) => {
			fontListItems.value = m.default.items as FontListItem[];
			return fontListItems.value;
		});
	}
	return fontListPromise;
}

function loadCustomFont(font: string, url: string): Promise<string> {
	return new FontFace(font, `url("${url}")`)
		.load()
		.then((face) => {
			document.fonts.add(face);
			return font;
		})
		.catch(() => {
			console.warn(`Failed to load custom font: ${font}`);
			return font;
		});
}

function loadGoogleFont(font: string, weight?: string): Promise<string> {
	return new Promise<string>((resolve) => {
		const attempt = (withWeight: boolean) => {
			const familyParam = withWeight
				? `${encodeURIComponent(font)}:wght@${weight}`
				: encodeURIComponent(font);
			const link = document.createElement("link");
			link.id = `gf-${font.replace(/\s+/g, "-")}${withWeight ? `-${weight}` : ""}`;
			link.rel = "stylesheet";
			link.crossOrigin = "anonymous";
			link.href = `${GF_CSS}?family=${familyParam}&display=swap`;
			link.addEventListener("load", () => resolve(font), { once: true });
			link.addEventListener(
				"error",
				() => {
					link.remove();
					if (withWeight) {
						// Single-weight faces (Italiana, Young Serif, Caprasimo…) 400 on ANY
						// wght@ request — the css2 API rejects weights a family doesn't carry.
						// Retry the family default; the browser synthesises the bold.
						attempt(false);
						return;
					}
					console.warn(`Failed to load font: ${font}`);
					resolve(font);
				},
				{ once: true },
			);
			document.head.appendChild(link);
		};
		attempt(!!weight);
	});
}

// A Font design token (fontFamily: var(--id)) stands in for its family, so every
// caller can work with the family without knowing whether a style is tokenized.
function resolveFontToken(font: string): string {
	if (!font.includes("var(")) return font;
	const { resolveVariableValue } = useBuilderToken();
	const resolved = resolveVariableValue(font);
	return resolved === font ? "" : resolved; // unknown token: no family to work with
}

export function setFont(font: string | null, weight?: string): Promise<string> {
	if (!font) return Promise.resolve("");

	// a token stands in for its family; an unknown one leaves nothing to load
	const family = font.includes("var(") ? resolveFontToken(font) : font;
	if (!family) return Promise.resolve(font);

	const cacheKey = weight ? `${family}:${weight}` : family;
	if (fontCache.has(cacheKey)) return fontCache.get(cacheKey)!;

	// userFont list resource may not have loaded yet (e.g. a page rendered right
	// after navigation); fall back to treating it as a Google font until it does.
	const customFont = (userFont.data || []).find(
		(f: { font_name: string; font_file: string }) => f.font_name === family,
	);

	const promise = customFont
		? loadCustomFont(family, customFont.font_file)
		: loadGoogleFont(family, weight);

	fontCache.set(cacheKey, promise);
	return promise;
}

const isCustomFont = (font: string) =>
	(userFont.data || []).some((f: { font_name: string }) => f.font_name === font);

// Google's text= parameter returns a face carrying only the requested characters, which
// for a preview is the family's own name — roughly 1KB rather than the full file.
async function loadSubsetFace(font: string): Promise<string> {
	const glyphs = [...new Set(font)].join("");
	const res = await fetch(`${GF_CSS}?family=${encodeURIComponent(font)}&text=${encodeURIComponent(glyphs)}`);
	if (!res.ok) throw new Error(`No Google font named ${font}`);
	const url = (await res.text()).match(/url\((https:\/\/[^)]+)\)/)?.[1];
	if (!url) throw new Error(`No font file in the stylesheet for ${font}`);

	const previewFamily = `${PREVIEW_PREFIX}${font}`;
	document.fonts.add(await new FontFace(previewFamily, `url("${url}")`).load());
	return previewFamily;
}

function resolvePreviewFace(font: string): Promise<string> {
	// a font already applied on the canvas has its full face on the way, and uploaded
	// fonts are served whole from the site itself — either way there is nothing to
	// subset, and setFont already caches both under the real family name
	return isCustomFont(font) || fontCache.has(font) ? setFont(font) : loadSubsetFace(font);
}

/** Loads just enough of a font to render its own name. Failures leave it unpreviewed. */
export function loadFontPreview(font: string): Promise<void> {
	const pending = previewRequests.get(font);
	if (pending) return pending;

	const request = resolvePreviewFace(font)
		.then((family) => {
			// swap the map so the pickers restyle once the face is actually usable
			previewFamilies.value = new Map(previewFamilies.value).set(font, family);
		})
		.catch(() => console.warn(`Failed to load font preview: ${font}`));

	previewRequests.set(font, request);
	return request;
}

const queuedPreviews = new Set<string>();
let flushTimer: ReturnType<typeof setTimeout> | undefined;

function flushPreviewQueue() {
	flushTimer = undefined;
	queuedPreviews.forEach(loadFontPreview);
	queuedPreviews.clear();
}

/** Queues previews for the currently visible options, coalescing bursts of keystrokes. */
export function schedulePreviewLoad(fonts: string[]): void {
	fonts.forEach((font) => {
		if (!previewRequests.has(font)) queuedPreviews.add(font);
	});
	// the window runs from the first queued font rather than the last, so previews still
	// arrive while someone is typing
	if (queuedPreviews.size && !flushTimer) flushTimer = setTimeout(flushPreviewQueue, PREVIEW_DEBOUNCE);
}

/**
 * Style for rendering a label in its own typeface. Returns undefined until the preview
 * has loaded, so the label stays in the UI font instead of flashing a fallback serif.
 */
export function previewFontStyle(font: string): { fontFamily: string } | undefined {
	const family = previewFamilies.value.get(font);
	// JSON.stringify quotes the family, which matters for names containing spaces
	return family ? { fontFamily: JSON.stringify(family) } : undefined;
}

export function setFontFromHTML(html: string): void {
	const matches = html.match(/font-family:\s*([^;"]+)[";]/g) ?? [];
	matches
		.map((m) => m.replace(/font-family:\s*([^;"]+)[";]/, "$1").trim())
		.filter(Boolean)
		.forEach((font) => setFont(font));
}

export function getFontWeightOptions(font: string): WeightOption[] {
	loadFontList();
	const family = font ? resolveFontToken(font) : font;
	const fontObj = family && fontListItems.value.find((f) => f.family === family);
	if (!fontObj) return [{ value: "400", label: "Regular" }];

	return fontObj.variants
		.filter((v) => !v.includes("italic"))
		.map((v) => {
			const value = (v === "regular" ? "400" : v) as FontWeight;
			return { value, label: WEIGHT_LABELS[value] ?? v };
		});
}

export { fontListItems };
