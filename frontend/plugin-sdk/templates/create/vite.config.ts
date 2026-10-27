import vue from "@vitejs/plugin-vue";
import builderPlugin from "frappe-builder-plugin-sdk/vite";
import tailwindcss from "tailwindcss";
import { defineConfig } from "vite";

export default defineConfig({
	css: { postcss: { plugins: [tailwindcss({ config: "./tailwind.config.js" })] } },
	plugins: [vue(), builderPlugin({ builderUrl: __BUILDER_URL__ })],
});
