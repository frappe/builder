import { Button, Dialog, FeatherIcon, FormControl, FrappeUI, createResource } from "frappe-ui";
import { createPinia } from "pinia";
import { createApp } from "vue";
import "./index.css";
import router from "./router";
import "./setupFrappeUIResource";
import "./utils/arrayFunctions";

import App from "@/App.vue";
import posthog from "posthog-js";

const app = createApp(App);
const pinia = createPinia();

app.use(router);
app.use(FrappeUI);
app.use(pinia);

window.name = "frappe-builder";

app.component("Button", Button);
app.component("FormControl", FormControl);
app.component("Dialog", Dialog);

app.component("FeatherIcon", FeatherIcon);
app.mount("#app");

declare global {
	interface Window {
		is_developer_mode?: boolean;
		posthog: typeof posthog;
	}
}
window.is_developer_mode = process.env.NODE_ENV === "development";

type PosthogSettings = {
	posthog_project_id: string;
	posthog_host: string;
	enable_telemetry: boolean;
	telemetry_site_age: number;
	record_session: boolean;
	posthog_identify: string;
};

createResource({
	url: "builder.api.get_posthog_settings",
	method: "GET",
	auto: true,
	onSuccess: (posthogSettings: PosthogSettings) => {
		if (!posthogSettings.enable_telemetry || !posthogSettings.posthog_project_id) {
			return;
		}
		posthog.init(posthogSettings.posthog_project_id, {
			api_host: posthogSettings.posthog_host,
			person_profiles: "identified_only",
			autocapture: false,
			capture_pageview: false,
			capture_pageleave: false,
			enable_heatmaps: false,
			disable_session_recording: false,
			loaded: (posthog) => {
				posthog.identify(window.location.hostname);
			},
		});
	},
});

window.posthog = posthog;
