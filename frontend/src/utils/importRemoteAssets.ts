import type Block from "@/block";
import { call, toast } from "frappe-ui";

const REMOTE_URL = /^https?:\/\//;

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
