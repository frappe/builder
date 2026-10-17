import vue from "@vitejs/plugin-vue";
import path from "node:path";
import builderExtension from "frappe-builder-extension-sdk/vite";
import tailwindcss from "tailwindcss";
import IconsEsbuild from "unplugin-icons/esbuild";
import Icons from "unplugin-icons/vite";
import { defineConfig } from "vite";

export default defineConfig({
	resolve: {
		alias: [
			{
				find: /^.*fonts\/Inter\/inter\.css$/,
				replacement: path.resolve("./src/no-fonts.css"),
			},
		],
	},
	css: { postcss: { plugins: [tailwindcss({ config: "./tailwind.config.js" })] } },
	plugins: [
		Icons({ compiler: "vue3" }),
		vue(),
		builderExtension({ builderUrl: __BUILDER_URL__ }),
	],
	optimizeDeps: {
		include: [
			"frappe-ui > feather-icons",
			"frappe-ui > debug",
			"engine.io-client",
			"interactjs",
			"highlight.js/lib/core",
		],
		esbuildOptions: { plugins: [IconsEsbuild({ compiler: "vue3" })] },
	},
});
