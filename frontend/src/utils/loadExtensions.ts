import { call } from "frappe-ui";
import type { App, Plugin } from "vue";

export type InstalledExtension = {
	name: string;
	label: string;
	entry_url: string;
	style_url?: string | null;
};

const addStyle = (url: string) => {
	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href = url;
	document.head.appendChild(link);
};

const isPlugin = (value: unknown): value is Plugin =>
	typeof value === "function" || typeof (value as { install?: unknown })?.install === "function";

/** The entry module's default export is a Vue plugin. Its own imports of "builder", "vue", "pinia" and "frappe-ui" resolve through the editor page's import map. */
export async function importExtension(extension: InstalledExtension): Promise<Plugin> {
	if (extension.style_url) addStyle(extension.style_url);
	const module = await import(/* @vite-ignore */ extension.entry_url);
	if (!isPlugin(module.default)) {
		throw new Error(`${extension.entry_url} has no default export with an install() function`);
	}
	return module.default;
}

type LoadedExtension = { extension: InstalledExtension; plugin: Plugin };

const report = (extension: InstalledExtension, error: unknown) =>
	console.error(`[builder] the extension "${extension.label}" did not load`, error);

/** An extension that fails to load is skipped, so the editor still starts. */
export async function importExtensions(): Promise<LoadedExtension[]> {
	const extensions: InstalledExtension[] = await call(
		"builder.builder.doctype.builder_extension.builder_extension.get_enabled_extensions",
	);
	const results = await Promise.allSettled(extensions.map(importExtension));
	return results.flatMap((result, index) => {
		if (result.status === "fulfilled") return [{ extension: extensions[index], plugin: result.value }];
		report(extensions[index], result.reason);
		return [];
	});
}

export function installExtensions(app: App, loaded: LoadedExtension[]) {
	for (const { extension, plugin } of loaded) {
		try {
			app.use(plugin);
		} catch (error) {
			report(extension, error);
		}
	}
}
