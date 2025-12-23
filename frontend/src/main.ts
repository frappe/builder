import { createApp } from "vue";

import { Button, FeatherIcon, FormControl, FrappeUI } from "frappe-ui";
import { createPinia } from "pinia";
import "./index.css";
import router from "./router";
import "./setupFrappeUIResource";
import "./telemetry";
import "./utils/arrayFunctions";

import App from "@/App.vue";
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import Input from "@/components/Controls/Input.vue";

const app = createApp(App);
const pinia = createPinia();

app.use(router);
app.use(FrappeUI);
app.use(pinia);

window.name = "frappe-builder";
app.config.globalProperties.window = window;

app.component("Button", Button);
app.component("BuilderButton", BuilderButton);
app.component("FormControl", FormControl);
app.component("BuilderInput", Input);

app.component("FeatherIcon", FeatherIcon);
app.mount("#app");

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
