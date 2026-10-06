import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));

/**
 * Builds `frappe-builder-extension-sdk`, the one module that each extension frame loads.
 *
 * The output goes to `builder/public/extension_sdk`. Builder serves it at
 * `/builder_extension_asset/sdk/`, with the CORS header that a null-origin frame needs.
 * The import map of the shell names the same URL. So no extension build
 * includes the SDK. One module copy serves the frame and its extension.
 */
export default defineConfig({
	// the public assets of the app do not belong to the SDK. Without this, Vite copies them here
	publicDir: false,
	build: {
		outDir: path.resolve(root, "../builder/public/extension_sdk"),
		emptyOutDir: true,
		// the frame runs module scripts. So it is always a modern browser
		target: "es2020",
		lib: {
			entry: path.resolve(root, "extension-sdk/src/sdk/index.ts"),
			formats: ["es"],
			fileName: () => "extension-sdk.js",
		},
	},
});
