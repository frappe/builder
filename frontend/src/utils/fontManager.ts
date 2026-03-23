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

function loadGoogleFont(font: string): Promise<string> {
	if (fontCache.has(font)) return fontCache.get(font)!;

	const linkId = `gf-${font.replace(/\s+/g, "-")}`;

	if (!document.getElementById(linkId)) {
		Object.assign(document.head.appendChild(document.createElement("link")), {
			id: linkId,
			rel: "stylesheet",
			crossOrigin: "anonymous",
			href: `${GF_CSS}?family=${encodeURIComponent(
				font,
			)}:wght@100;200;300;400;500;600;700;800;900&display=swap`,
		});
	}

	const promise = new Promise<string>((resolve) => {
		const link = document.getElementById(linkId) as HTMLLinkElement;
		link.addEventListener("load", () => resolve(font), { once: true });
		link.addEventListener(
			"error",
			() => {
				console.warn(`Failed to load font: ${font}`);
				resolve(font);
			},
			{ once: true },
		);
	});

	fontCache.set(font, promise);
	return promise;
}

export function setFont(font: string | null): Promise<string> {
	if (!font) return Promise.resolve("");

	const customFont = userFont.data.find(
		(f: { font_name: string; font_file: string }) => f.font_name === font,
	);
	if (customFont) {
		if (!fontCache.has(font)) {
			fontCache.set(
				font,
				new FontFace(font, `url("${customFont.font_file}")`).load().then((face) => {
					document.fonts.add(face);
					return font;
				}),
			);
		}
		return fontCache.get(font)!;
	}

	return loadGoogleFont(font);
}

export function setFontFromHTML(html: string): void {
	(html.match(/font-family:\s*([^;"]+)[";]/g) ?? [])
		.map((m) => m.replace(/font-family:\s*([^;"]+)[";]/, "$1").trim())
		.filter(Boolean)
		.forEach((font) => setFont(font));
}

export function getFontWeightOptions(font: string): WeightOption[] {
	const fallback = [{ value: "400" as FontWeight, label: "Regular" }];
	const fontObj = font && fontList.items.find((f) => f.family === font);
	if (!fontObj) return fallback;

	return fontObj.variants
		.filter((v) => !v.includes("italic"))
		.map((v) => {
			const value = (v === "regular" ? "400" : v) as FontWeight;
			return { value, label: WEIGHT_LABELS[value] ?? v };
		});
}

export { fontList };
