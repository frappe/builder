import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));
const entry = (file: string) => path.resolve(root, "src", file);

/**
 * Builds the npm package. Run it only before a publish. `publishConfig` points `exports` to `dist`.
 * `vue` and the SDK stay external. The frame gives the SDK, and the extension gives Vue.
 */
export default defineConfig({
	build: {
		outDir: path.resolve(root, "dist"),
		emptyOutDir: true,
		target: "es2020",
		lib: {
			entry: {
				index: entry("index.ts"),
				vue: entry("vue.ts"),
				types: entry("shared/types.ts"),
				"transport/createPortChannel": entry("shared/transport/createPortChannel.ts"),
			},
			formats: ["es"],
		},
		rollupOptions: { external: ["vue", "frappe-builder-extension-sdk"] },
	},
});
