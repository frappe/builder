import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));
const entry = (file: string) => path.resolve(root, "src", file);

/**
 * Builds the tarball an extension author installs from npm.
 *
 * The repo resolves this package through `exports`, which point at `src`, so
 * this build runs only before a publish. `publishConfig` swaps those same
 * `exports` over to `dist`.
 *
 * `vue` stays external because the SDK ships no Vue runtime. The author's own
 * copy must be the one that renders a slot. The package name stays external for
 * the same reason: `vue.ts` must keep importing the SDK by its bare specifier,
 * which the frame's import map resolves to the one instance Builder serves.
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
				types: entry("types.ts"),
				"transport/createPortChannel": entry("transport/createPortChannel.ts"),
			},
			formats: ["es"],
		},
		rollupOptions: { external: ["vue", "frappe-builder-extension-sdk"] },
	},
});
