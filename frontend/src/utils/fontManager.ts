import userFont from "@/data/userFonts";
import fontList from "@/utils/fontList.json";

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
const fontCache = new WeakMap<Document, Map<string, Promise<string>>>();

function loadCustomFont(font: string, url: string, targetDocument: Document): Promise<string> {
	const FontFaceConstructor = targetDocument.defaultView?.FontFace || FontFace;
	return new FontFaceConstructor(font, `url("${url}")`)
		.load()
		.then((face) => {
			targetDocument.fonts.add(face);
			return font;
		})
		.catch(() => {
			console.warn(`Failed to load custom font: ${font}`);
			return font;
		});
}

function loadGoogleFont(font: string, weight: string | undefined, targetDocument: Document): Promise<string> {
	const familyParam = weight ? `${encodeURIComponent(font)}:wght@${weight}` : encodeURIComponent(font);

	return new Promise<string>((resolve) => {
		const id = `gf-${font.replace(/\s+/g, "-")}${weight ? `-${weight}` : ""}`;
		const existing = targetDocument.getElementById(id);
		if (existing) {
			resolve(font);
			return;
		}
		const link = targetDocument.createElement("link");
		link.id = id;
		link.rel = "stylesheet";
		link.crossOrigin = "anonymous";
		link.href = `${GF_CSS}?family=${familyParam}&display=swap`;
		link.addEventListener("load", () => resolve(font), { once: true });
		link.addEventListener(
			"error",
			() => {
				console.warn(`Failed to load font: ${font}`);
				resolve(font);
			},
			{ once: true },
		);
		targetDocument.head.appendChild(link);
	});
}

export function setFont(
	font: string | null,
	weight?: string,
	targetDocument: Document = document,
): Promise<string> {
	if (!font) return Promise.resolve("");
	const cacheKey = weight ? `${font}:${weight}` : font;
	let documentCache = fontCache.get(targetDocument);
	if (!documentCache) {
		documentCache = new Map();
		fontCache.set(targetDocument, documentCache);
	}
	if (documentCache.has(cacheKey)) return documentCache.get(cacheKey)!;

	// userFont list resource may not have loaded yet (e.g. a page rendered right
	// after navigation); fall back to treating it as a Google font until it does.
	const customFont = (userFont.data || []).find(
		(f: { font_name: string; font_file: string }) => f.font_name === font,
	);

	const promise = customFont
		? loadCustomFont(font, customFont.font_file, targetDocument)
		: loadGoogleFont(font, weight, targetDocument);

	documentCache.set(cacheKey, promise);
	return promise;
}

export function setFontFromHTML(html: string, targetDocument: Document = document): void {
	const matches = html.match(/font-family:\s*([^;"]+)[";]/g) ?? [];
	matches
		.map((m) => m.replace(/font-family:\s*([^;"]+)[";]/, "$1").trim())
		.filter(Boolean)
		.forEach((font) => setFont(font, undefined, targetDocument));
}

export function getFontWeightOptions(font: string): WeightOption[] {
	const fontObj = font && fontList.items.find((f) => f.family === font);
	if (!fontObj) return [{ value: "400", label: "Regular" }];

	return fontObj.variants
		.filter((v) => !v.includes("italic"))
		.map((v) => {
			const value = (v === "regular" ? "400" : v) as FontWeight;
			return { value, label: WEIGHT_LABELS[value] ?? v };
		});
}

export { fontList };
