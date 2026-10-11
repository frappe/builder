import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));
const entry = (file: string) => path.resolve(root, "src", file);

/**
 * Builds the package that an extension author installs from npm.
 *
 * In this repo, `exports` points to `src`. So this build runs only before a
 * publish. `publishConfig` changes the same `exports` to point to `dist`.
 *
 * `vue` stays external, because the SDK has no Vue runtime. The copy of the
 * author must show the slot. The package name stays external for the same
 * reason. `vue.ts` must import the SDK by its package name. The import map of
 * the frame points that name to the one SDK copy that Builder serves.
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
