// first: in the editor demo it also walls off the site's storage before anything reads it
import "./setupFrappeUIResource";
import { createApp } from "vue";

import { Button, FormControl, FrappeUI } from "frappe-ui";
import { telemetryPlugin } from "@framework/ui/telemetry";
import { createPinia } from "pinia";
import "./index.css";
import router from "./router";
import translationPlugin, { ensureTranslations } from "./translation";

import App from "@/App.vue";
import Input from "@/components/Controls/Input.vue";
import { editorDemo } from "@/utils/editorDemo";

const app = createApp(App);
const pinia = createPinia();

// pinia first: installing the router starts the first navigation, and a route
// chunk looks up stores as it loads
app.use(pinia);

ensureTranslations().then(() => {
	app.use(router);
	app.use(FrappeUI);
	if (!editorDemo) {
		app.use(telemetryPlugin, { app_name: "builder" });
		// the demo runs inside the published page, where these names would capture its edit link
		window.name = "frappe-builder";
	}
	app.use(translationPlugin);

	app.config.globalProperties.window = window;

	app.component("Button", Button);
	app.component("FormControl", FormControl);
	app.component("BuilderInput", Input);

	app.mount("#app");
});

declare global {
	interface Window {
		is_developer_mode?: boolean;
		builder_version: string;
	}
}

if (window.is_developer_mode && typeof window.is_developer_mode === "string") {
	window.is_developer_mode =
		window.is_developer_mode === "1" ||
		window.is_developer_mode === "True" ||
		(window.is_developer_mode as string).startsWith("{{");
}

if (window.builder_version && window.builder_version.startsWith("{{")) {
	window.builder_version = "develop";
}
