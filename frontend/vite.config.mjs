import vue from "@vitejs/plugin-vue";
import frameworkUI from "@framework/ui/vite";
import frappeui from "frappe-ui/vite";
import fs from "fs";
import path from "path";
import { defineConfig } from "vite";

// the dev server renders no boot data, so the socket.io port reaches the page at build time
function socketioPort() {
	const config = path.resolve(import.meta.dirname, "../../../sites/common_site_config.json");
	const port =
		process.env.FRAPPE_SOCKETIO_PORT ||
		(fs.existsSync(config) && JSON.parse(fs.readFileSync(config, "utf8")).socketio_port);
	return String(port || "");
}

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
		"import.meta.env.VITE_SOCKETIO_PORT": JSON.stringify(socketioPort()),
	},
	plugins: [
		frappeui({
			frontendRoute: "/_builder",
			// Resolved from the bench layout when one is around; stated here so a
			// standalone checkout builds too.
			buildConfig: { indexHtmlPath: "../builder/www/_builder.html" },
			frappeProxy: {
				port: 8080,
				source: "^/(app|desk|login|api|assets|files|pages|builder_assets)",
			},
			lucideIcons: true,
			// this app brings its own @codemirror/lang-* packages and never imports
			// frappe-ui/code-editor, so the language-stubbing plugin has nothing to do
			codeLanguages: false,
			frappeTypes: {
				input: {
					builder: [
						"block_template",
						"builder_ai_model",
						"builder_ai_provider",
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
		frameworkUI(),
	],
	build: {
		chunkSizeWarningLimit: 1500,
		target: "es2015",
	},
	resolve: {
		dedupe: ["prosemirror-model", "prosemirror-view", "prosemirror-state", "prosemirror-transform"],
		alias: {
			"@": path.resolve(import.meta.dirname, "src"),
		},
	},
	server: {
		allowedHosts: true,
		proxy: {
			"^/(?!(?:builder|_builder|app|desk|login|api|assets|files|private|pages|builder_assets|src|node_modules)(?:[/?#]|$)|@|__)(?![^?]*\\.)[^/?#].*":
				{
					target: `http://127.0.0.1:${process.env.FRAPPE_WEB_SERVER_PORT || 8000}`,
					router: (req) =>
						`http://${req.headers.host.split(":")[0]}:${process.env.FRAPPE_WEB_SERVER_PORT || 8000}`,
				},
		},
	},
	optimizeDeps: {
		include: ["engine.io-client", "highlight.js/lib/core"],
	},
});
