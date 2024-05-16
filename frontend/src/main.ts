import { Button, Dialog, FeatherIcon, FormControl, FrappeUI, Input } from "frappe-ui";
import { createPinia } from "pinia";
import { createApp } from "vue";
import "./index.css";
import router from "./router";
import "./setupFrappeUIResource";
import "./utils/arrayFunctions";

import App from "@/App.vue";

const app = createApp(App);
const pinia = createPinia();

app.use(router);
app.use(FrappeUI);
app.use(pinia);

window.name = "frappe-builder";

app.component("Button", Button);
app.component("Input", Input);
app.component("FormControl", FormControl);
app.component("Dialog", Dialog);

app.component("FeatherIcon", FeatherIcon);
app.mount("#app");

declare global {
	interface Window {
		is_developer_mode?: boolean;
	}
}
window.is_developer_mode = process.env.NODE_ENV === "development";
