import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));

/**
 * Builds `frappe-builder-extension-sdk`, the one module every extension frame loads.
 *
 * It lands in `builder/public/extension_sdk`, which Builder serves at
 * `/builder_extension_asset/sdk/` with the CORS header a null-origin frame needs.
 * The shell's import map names that same URL, so the SDK stays external to every
 * extension build and one module instance serves the frame and its extension.
 */
export default defineConfig({
	// the app's public assets are not the SDK's, and Vite would copy them here
	publicDir: false,
	build: {
		outDir: path.resolve(root, "../builder/public/extension_sdk"),
		emptyOutDir: true,
		// the frame is a modern browser by definition: it runs module scripts
		target: "es2020",
		lib: {
			entry: path.resolve(root, "extension-sdk/src/sdk/index.ts"),
			formats: ["es"],
			fileName: () => "extension-sdk.js",
		},
	},
});
