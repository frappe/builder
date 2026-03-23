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
const fontCache = new Map<string, Promise<string>>();

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

function loadGoogleFont(font: string): Promise<string> {
	return new Promise<string>((resolve) => {
		const link = document.createElement("link");
		link.id = `gf-${font.replace(/\s+/g, "-")}`;
		link.rel = "stylesheet";
		link.crossOrigin = "anonymous";
		link.href = `${GF_CSS}?family=${encodeURIComponent(font)}&display=swap`;
		link.addEventListener("load", () => resolve(font), { once: true });
		link.addEventListener(
			"error",
			() => {
				console.warn(`Failed to load font: ${font}`);
				resolve(font);
			},
			{ once: true },
		);
		document.head.appendChild(link);
	});
}

export function setFont(font: string | null): Promise<string> {
	if (!font) return Promise.resolve("");
	if (fontCache.has(font)) return fontCache.get(font)!;

	const customFont = userFont.data.find(
		(f: { font_name: string; font_file: string }) => f.font_name === font,
	);

	const promise = customFont ? loadCustomFont(font, customFont.font_file) : loadGoogleFont(font);

	fontCache.set(font, promise);
	return promise;
}

export function setFontFromHTML(html: string): void {
	const matches = html.match(/font-family:\s*([^;"]+)[";]/g) ?? [];
	matches
		.map((m) => m.replace(/font-family:\s*([^;"]+)[";]/, "$1").trim())
		.filter(Boolean)
		.forEach((font) => setFont(font));
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
