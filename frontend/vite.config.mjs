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
			frontendRoute: "/_builder",
			frappeProxy: {
				port: 8080,
				source: "^/(app|desk|login|api|assets|files|pages|builder_assets)",
			},
			lucideIcons: true,
			frappeTypes: {
				input: {
					builder: [
						"block_template",
						"builder_client_script",
						"builder_component",
						"builder_page",
						"builder_page_client_script",
						"builder_project_folder",
						"builder_settings",
						"builder_variable",
						"user_font",
					],
				},
			},
		}),
		vue(),
	],
	build: {
		chunkSizeWarningLimit: 1500,
		target: "es2015",
	},
	resolve: {
		dedupe: ["prosemirror-model", "prosemirror-view", "prosemirror-state", "prosemirror-transform"],
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	server: {
		allowedHosts: true,
	},
	optimizeDeps: {
		include: ["frappe-ui > feather-icons", "engine.io-client", "interactjs", "highlight.js/lib/core"],
	},
});
