import type Block from "@/block";
import userFont from "@/data/userFonts";
import { registerCustomFont } from "@/utils/fontManager";
import { call, toast } from "frappe-ui";

const REMOTE_URL = /^https?:\/\//;

export type RemoteFont = { family: string; url: string; weight?: string; style?: string };

/**
 * Blocks pasted from another site keep pointing at that site's images. Pulling them
 * into this site is what makes the copy stand on its own: the page keeps working when
 * the source changes, images go through Builder's own optimisation, and nothing leaks
 * traffic to a third party.
 */
export function collectRemoteAssets(blocks: (Block | BlockOptions)[]): string[] {
	const urls = new Set<string>();
	blocks.forEach((block) => walk(block as BlockOptions, urls));
	return [...urls];
}

export async function importRemoteAssets(blocks: (Block | BlockOptions)[], urls: string[]) {
	toast.loading(`Importing ${urls.length} images...`, { id: "import-assets" });
	try {
		const map = (await call("builder.api.import_remote_assets", { urls })) as Record<string, string>;
		const imported = Object.keys(map).length;
		blocks.forEach((block) => rewrite(block as BlockOptions, map));
		toast.success(`Imported ${imported} of ${urls.length} images`, { id: "import-assets" });
		return map;
	} catch (error: any) {
		toast.error("Could not import images", {
			id: "import-assets",
			description: error?.message || "",
		});
		return {};
	}
}

/**
 * A webfont left pointing at the site it came from is the asset most likely to fail
 * outright, since self hosted fonts are rarely served with the CORS headers a cross
 * origin font needs. Recreating each family as a User Font also puts it in Builder's
 * font picker. Builder stores one file per family, so only the most ordinary face of
 * each family comes across and other weights are synthesised.
 */
export async function importRemoteFonts(fonts: RemoteFont[]) {
	if (!fonts.length) return {};
	toast.loading(`Importing ${fonts.length} fonts...`, { id: "import-fonts" });
	try {
		const map = (await call("builder.api.import_remote_fonts", { fonts })) as Record<string, string>;
		await Promise.all(Object.entries(map).map(([family, url]) => registerCustomFont(family, url)));
		await userFont.fetch();
		toast.success(`Imported ${Object.keys(map).length} of ${fonts.length} fonts`, { id: "import-fonts" });
		return map;
	} catch (error: any) {
		toast.error("Could not import fonts", { id: "import-fonts", description: error?.message || "" });
		return {};
	}
}

/**
 * The copied page carries the original @font-face rules in its head so it renders
 * before anything is imported. Once a family is a User Font those rules would win on
 * the published page, since head HTML is written after Builder's own font styles.
 */
export function dropImportedFontFaces(headHtml: string, families: string[]): string {
	if (!headHtml || !families.length) return headHtml;
	const lower = families.map((family) => family.toLowerCase());

	let html = headHtml.replace(/@font-face\s*{[^}]*}/gi, (rule) => {
		const family = rule.match(/font-family\s*:\s*["']?([^;"'}]+)/i)?.[1]?.trim().toLowerCase();
		return family && lower.includes(family) ? "" : rule;
	});

	// a Google Fonts link for a family that now lives here is just a request to a
	// third party for a file the site already has
	html = html.replace(/<link\b[^>]*fonts\.googleapis\.com[^>]*>/gi, (link) => {
		const families = [...link.matchAll(/family=([^&"'>]+)/gi)].map((match) =>
			decodeURIComponent(match[1]).split(":")[0].replace(/\+/g, " ").toLowerCase(),
		);
		return families.length && families.every((family) => lower.includes(family)) ? "" : link;
	});

	// whatever is left of a style element that held nothing but those faces
	html = html.replace(/<style>\s*<\/style>/gi, "");
	return html.replace(/\n{2,}/g, "\n").trim();
}

function walk(block: BlockOptions, urls: Set<string>) {
	for (const attribute of ["src", "darkSrc", "poster"]) {
		const value = block.attributes?.[attribute];
		if (typeof value === "string" && REMOTE_URL.test(value)) urls.add(value);
	}
	for (const styles of styleMaps(block)) {
		for (const url of backgroundUrls(styles.backgroundImage)) urls.add(url);
	}
	block.children?.forEach((child) => walk(child as BlockOptions, urls));
}

function rewrite(block: BlockOptions, map: Record<string, string>) {
	for (const attribute of ["src", "darkSrc", "poster"]) {
		const value = block.attributes?.[attribute];
		if (typeof value === "string" && map[value]) block.attributes![attribute] = map[value];
	}
	for (const styles of styleMaps(block)) {
		const background = styles.backgroundImage;
		if (typeof background !== "string") continue;
		let updated = background;
		for (const url of backgroundUrls(background)) {
			if (map[url]) updated = updated.split(url).join(map[url]);
		}
		if (updated !== background) styles.backgroundImage = updated;
	}
	block.children?.forEach((child) => rewrite(child as BlockOptions, map));
}

function styleMaps(block: BlockOptions): BlockStyleMap[] {
	return [block.baseStyles, block.tabletStyles, block.mobileStyles].filter(Boolean) as BlockStyleMap[];
}

function backgroundUrls(background: unknown): string[] {
	if (typeof background !== "string" || !background.includes("url(")) return [];
	return [...background.matchAll(/url\((['"]?)([^'")]+)\1\)/g)]
		.map((match) => match[2])
		.filter((url) => REMOTE_URL.test(url));
}
