import path from "node:path";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
	// frappe-ui exports only its root, and the root loads .vue files
	plugins: [vue()],
	resolve: {
		alias: { "@": path.resolve(__dirname, "src") },
	},
	test: {
		include: ["src/**/*.test.ts", "extension-sdk/src/**/*.test.ts"],
	},
});
