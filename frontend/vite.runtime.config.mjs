import path from "path";
import { defineConfig } from "vite";

const reactivityBrowser = path.resolve(
	__dirname,
	"../node_modules/@vue/reactivity/dist/reactivity.esm-browser.js",
);

export default defineConfig({
	define: {
		"process.env.NODE_ENV": JSON.stringify("production"),
	},
	resolve: {
		alias: {
			"@vue/reactivity": reactivityBrowser,
		},
	},
	build: {
		// Don't copy frontend/public assets into builder/public/js
		copyPublicDir: false,
		lib: {
			entry: path.resolve(__dirname, "src/runtime/reactivity.ts"),
			name: "reactivity",
			formats: ["iife"],
			fileName: () => "reactivity.js",
		},
		outDir: path.resolve(__dirname, "../builder/public/js"),
		emptyOutDir: false,
		target: "es2015",
		minify: true,
	},
});
