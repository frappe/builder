import { Button, FeatherIcon, FormControl, FrappeUI, Input } from "frappe-ui";
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
// eslint-disable-next-line vue/multi-word-component-names, vue/no-reserved-component-names
app.component("Button", Button);
app.component("Input", Input);
app.component("FormControl", FormControl);

app.component("FeatherIcon", FeatherIcon);
app.mount("#app");
