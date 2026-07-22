import userFont from "@/data/userFonts";
import { useBuilderToken } from "@/utils/useBuilderToken";
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

export function setFont(font: string | null, weight?: string): Promise<string> {
	if (!font) return Promise.resolve("");
	// A Font design token (fontFamily: var(--id)) resolves to its family before
	// loading — no caller needs to know whether a style is tokenized.
	if (font.includes("var(")) {
		const { resolveVariableValue } = useBuilderToken();
		const resolved = resolveVariableValue(font);
		if (resolved === font) return Promise.resolve(font); // unknown token: nothing to load
		font = resolved;
	}
	const cacheKey = weight ? `${font}:${weight}` : font;
	if (fontCache.has(cacheKey)) return fontCache.get(cacheKey)!;

	// userFont list resource may not have loaded yet (e.g. a page rendered right
	// after navigation); fall back to treating it as a Google font until it does.
	const customFont = (userFont.data || []).find(
		(f: { font_name: string; font_file: string }) => f.font_name === font,
	);

	const promise = customFont ? loadCustomFont(font, customFont.font_file) : loadGoogleFont(font, weight);

	fontCache.set(cacheKey, promise);
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
