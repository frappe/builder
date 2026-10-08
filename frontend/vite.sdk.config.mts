import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));

/**
 * Builds the SDK module that each extension frame loads, into `builder/public/extension_sdk`.
 * Builder serves it with a CORS header. The import map of the frame names the same URL.
 */
export default defineConfig({
	// Do not copy the public files of the app into the SDK output.
	publicDir: false,
	build: {
		outDir: path.resolve(root, "../builder/public/extension_sdk"),
		emptyOutDir: true,
		// The frame runs module scripts. So the browser is always modern.
		target: "es2020",
		lib: {
			entry: path.resolve(root, "extension-sdk/src/runtime/index.ts"),
			formats: ["es"],
			fileName: () => "extension-sdk.js",
		},
	},
});
