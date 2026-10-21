import vue from "@vitejs/plugin-vue";
import builderExtension from "frappe-builder-extension-sdk/vite";
import tailwindcss from "tailwindcss";
import { defineConfig } from "vite";

export default defineConfig({
	css: { postcss: { plugins: [tailwindcss({ config: "./tailwind.config.js" })] } },
	plugins: [vue(), builderExtension({ builderUrl: __BUILDER_URL__ })],
});
