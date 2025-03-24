import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import path from "path";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	plugins: [
		frappeui({
			frappeProxy: {
				port: 8080,
				source: "^/(app|login|api|assets|files|pages|builder_assets)",
			},
		}),
		vue(),
	],
	buildConfig: {
		indexHtmlPath: "../builder/www/_builder.html",
		outDir: `../builder/public/frontend`,
		baseUrl: "/assets/builder/frontend/",
		emptyOutDir: true,
		target: "es2015",
	},
	build: {
		chunkSizeWarningLimit: 1500,
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	server: {
		allowedHosts: true,
	},
	optimizeDeps: {
		include: ["frappe-ui > feather-icons", "showdown", "engine.io-client"],
	},
});
