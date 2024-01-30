import App from "@/App.vue";
import {
	Button,
	Dialog,
	FeatherIcon,
	FormControl,
	FrappeUI,
	Input,
	frappeRequest,
	setConfig,
} from "frappe-ui";
import { createPinia } from "pinia";
import { createApp } from "vue";
import "./index.css";
import router from "./router";
import "./utils/arrayFunctions";

const app = createApp(App);
const pinia = createPinia();

setConfig("resourceFetcher", frappeRequest);

app.use(router);
app.use(FrappeUI);
app.use(pinia);

// eslint-disable-next-line vue/multi-word-component-names, vue/no-reserved-component-names
app.component("Button", Button);
app.component("Input", Input);
app.component("FormControl", FormControl);
app.component("Dialog", Dialog);

app.component("FeatherIcon", FeatherIcon);
app.mount("#app");
