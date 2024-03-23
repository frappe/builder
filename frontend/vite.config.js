import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import frappeui from "frappe-ui/vite";

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	plugins: [frappeui({ regex: "^/(app|login|api|assets|files|pages)" }), vue()],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: `../builder/public/frontend`,
		emptyOutDir: true,
		target: "es2015",
		sourcemap: true,
	},
	optimizeDeps: {
		include: ["frappe-ui > feather-icons", "showdown", "engine.io-client"],
	},
});
