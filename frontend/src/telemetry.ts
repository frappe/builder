import { createResource } from "frappe-ui";
import "../../../frappe/frappe/public/js/lib/posthog.js";

declare global {
	interface Window {
		posthog: {
			init: (projectToken: string, options: any) => void;
			identify: (userId: string) => void;
			startSessionRecording: () => void;
			capture: (eventName: string, data?: any) => void;
		};
	}
}

type PosthogSettings = {
	posthog_project_id: string;
	posthog_host: string;
	enable_telemetry: boolean;
	telemetry_site_age: number;
	record_session: boolean;
	posthog_identify: string;
};

const posthog = window.posthog;

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
			loaded: (ph: typeof posthog) => {
				ph.identify(posthogSettings?.posthog_identify || window.location.host);
				if (posthogSettings.record_session) {
					ph.startSessionRecording();
				}
			},
		});
	},
});

export { posthog };
