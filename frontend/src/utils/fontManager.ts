import userFont from "@/data/userFonts";
import { useBuilderToken } from "@/utils/useBuilderToken";
import { shallowRef } from "vue";
import { __ } from "@/translation";

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
	"100": __("Thin"),
	"200": __("Extra Light"),
	"300": __("Light"),
	"400": __("Regular"),
	"500": __("Medium"),
	"600": __("Semi Bold"),
	"700": __("Bold"),
	"800": __("Extra Bold"),
	"900": __("Black"),
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
// a builder session runs for hours: without a ceiling, browsing the picker would leave
// the whole catalog resident. Well above the ~20 rows on screen, so nothing visible goes.
const PREVIEW_FACE_LIMIT = 150;

const previewRequests = new Map<string, Promise<void>>();
// family -> the family its preview renders with; reactive so pickers restyle on arrival
const previewFamilies = shallowRef(new Map<string, string>());
// only subset faces, in insertion order — real faces belong to blocks and are never evicted
const previewFaces = new Map<string, FontFace>();

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

/** Does this family actually carry the weight? The css2 API answers a wght@ it
 * doesn't have with a 400 — which the browser then reports as a CORS failure,
 * since an error response carries no allow-origin header. Asking the catalogue
 * first turns a guaranteed round trip plus retry into a lookup. */
async function carriesWeight(font: string, weight: string): Promise<boolean> {
	const items = fontListItems.value.length ? fontListItems.value : await loadFontList().catch(() => []);
	const entry = items.find((item) => item.family === font);
	// Unknown family: let the request decide, the retry below still covers it.
	if (!entry) return true;
	return entry.variants.includes(weight) || (weight === "400" && entry.variants.includes("regular"));
}

async function loadGoogleFont(font: string, weight?: string): Promise<string> {
	if (weight && !(await carriesWeight(font, weight))) weight = undefined;
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

	const promise = customFont ? loadCustomFont(family, customFont.font_file) : loadGoogleFont(family, weight);

	fontCache.set(cacheKey, promise);
	return promise;
}

/**
 * Makes a family that has just become a User Font usable straight away. Whatever the
 * family resolved to before (usually a failed Google Fonts lookup) is cached, so the
 * old answer has to be dropped or the canvas keeps showing the fallback until reload.
 */
export function registerCustomFont(font: string, url: string): Promise<string> {
	for (const key of [...fontCache.keys()]) {
		if (key === font || key.startsWith(`${font}:`)) fontCache.delete(key);
	}
	const promise = loadCustomFont(font, url);
	fontCache.set(font, promise);
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
	const face = await new FontFace(previewFamily, `url("${url}")`).load();
	document.fonts.add(face);
	previewFaces.set(font, face);
	evictOldestPreviews();
	return previewFamily;
}

function evictOldestPreviews() {
	if (previewFaces.size <= PREVIEW_FACE_LIMIT) return;

	const families = new Map(previewFamilies.value);
	while (previewFaces.size > PREVIEW_FACE_LIMIT) {
		const [oldest, face] = previewFaces.entries().next().value!;
		document.fonts.delete(face);
		previewFaces.delete(oldest);
		// drop the request too, so the font can be previewed again if it comes back
		previewRequests.delete(oldest);
		families.delete(oldest);
	}
	previewFamilies.value = families;
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

let queuedPreviews: string[] = [];
let flushTimer: ReturnType<typeof setTimeout> | undefined;

function flushPreviewQueue() {
	flushTimer = undefined;
	queuedPreviews.forEach(loadFontPreview);
	queuedPreviews = [];
}

/** Queues previews for the currently visible options, coalescing bursts of keystrokes. */
export function enqueuePreviewLoad(fonts: string[]): void {
	// every keystroke supersedes the last, so the pending set is replaced rather than
	// accumulated: pausing on "rob" should not also fetch what matched "r"
	queuedPreviews = fonts.filter((font) => !previewRequests.has(font));
	if (flushTimer) clearTimeout(flushTimer);
	if (queuedPreviews.length) flushTimer = setTimeout(flushPreviewQueue, PREVIEW_DEBOUNCE);
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
	if (!fontObj) return [{ value: "400", label: __("Regular") }];

	return fontObj.variants
		.filter((v) => !v.includes("italic"))
		.map((v) => {
			const value = (v === "regular" ? "400" : v) as FontWeight;
			return { value, label: WEIGHT_LABELS[value] ?? v };
		});
}

export { fontListItems };
