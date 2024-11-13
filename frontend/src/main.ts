import { Button, Dialog, FeatherIcon, FormControl, FrappeUI } from "frappe-ui";
import { createPinia } from "pinia";
import { createApp } from "vue";
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

app.component("Button", Button);
app.component("BuilderButton", BuilderButton);
app.component("FormControl", FormControl);
app.component("Dialog", Dialog);
app.component("BuilderInput", Input);

app.component("FeatherIcon", FeatherIcon);
app.mount("#app");

declare global {
	interface Window {
		is_developer_mode?: boolean;
		trial_mode?: boolean;
	}
}
window.is_developer_mode = process.env.NODE_ENV === "development";
